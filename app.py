import streamlit as st
import subprocess
import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
import pandas as pd
from deepgram import DeepgramClient, PrerecordedOptions, SpeakOptions
import asyncio
import re
import pyaudio
import wave
import tempfile
from io import BytesIO
import time

# Load environment variables
load_dotenv()

# Configure all services
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-001')

# Initialize Deepgram v3/v4 client for both STT and TTS
deepgram = DeepgramClient(os.getenv("DEEPGRAM_API_KEY"))

class SmartFileSystemTool:
    def __init__(self):
        self.compile_c_program()
        self.file_cache = None
        self.last_update = None
    
    def compile_c_program(self):
        """Compile the C program"""
        if not os.path.exists("file_lister.exe"):
            result = subprocess.run(
                ["gcc", "-o", "file_lister.exe", "file_lister.c", "-ladvapi32"],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                st.error(f"Compilation error: {result.stderr}")
    
    def get_all_files(self, force_refresh=False):
        """Get all files with caching"""
        if not force_refresh and self.file_cache:
            return self.file_cache
        
        try:
            result = subprocess.run(["./file_lister.exe"], capture_output=True, text=True)
            data = json.loads(result.stdout)
            self.file_cache = data
            self.last_update = datetime.now()
            return data
        except Exception as e:
            st.error(f"Error getting files: {e}")
            return {"files": [], "total_files": 0}
    
    def find_file(self, filename):
        """Find a specific file by name (fuzzy matching)"""
        data = self.get_all_files()
        filename_lower = filename.lower()
        
        # Exact match
        for file in data['files']:
            if file['name'].lower() == filename_lower:
                return file
        
        # Partial match
        for file in data['files']:
            if filename_lower in file['name'].lower():
                return file
        
        return None
    
    def clean_text_for_speech(self, text):
        """Clean text for TTS - remove markdown and formatting"""
        # Remove markdown bold/italic markers
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold **text**
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Remove italic *text*
        text = re.sub(r'__([^_]+)__', r'\1', text)      # Remove bold __text__
        text = re.sub(r'_([^_]+)_', r'\1', text)        # Remove italic _text_
        
        # Remove markdown headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Remove code blocks
        text = re.sub(r'```[^`]*```', '', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Remove links but keep the text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove bullet points and list markers
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Clean up extra whitespace
        text = re.sub(r'\n\s*\n', '\n', text)
        text = re.sub(r' +', ' ', text)
        text = text.strip()
        
        return text
    
    def query_files(self, query):
        """Smart query processor for natural language"""
        data = self.get_all_files()
        query_lower = query.lower()
        
        # Check if user wants to create a file
        create_patterns = [
            r"create (?:a )?(?:file (?:named|called) )?([^\s]+)",
            r"make (?:a )?(?:file (?:named|called) )?([^\s]+)",
            r"create ([^\s]+) file",
            r"new file ([^\s]+)"
        ]
        
        for pattern in create_patterns:
            match = re.search(pattern, query_lower)
            if match:
                filename = match.group(1)
                # Check if content is specified
                content_match = re.search(r"with content[:\s]+(.+)", query, re.IGNORECASE)
                content = content_match.group(1) if content_match else ""
                
                success, result = create_custom_file(filename, content)
                if success:
                    # Refresh file list
                    self.get_all_files(force_refresh=True)
                    return f"✅ Successfully created file '{result}'! The file has been added to your directory. You can now query its properties or list all files to see it."
                else:
                    return f"❌ Failed to create file: {result}"
        
        # Check if user wants to delete a file
        delete_patterns = [
            r"delete (?:file )?([^\s]+)",
            r"remove (?:file )?([^\s]+)",
            r"delete ([^\s]+) file",
            r"remove ([^\s]+) file"
        ]
        
        for pattern in delete_patterns:
            match = re.search(pattern, query_lower)
            if match:
                filename = match.group(1)
                # Find the actual file (case-insensitive)
                file_info = self.find_file(filename)
                if file_info:
                    success, result = delete_file(file_info['name'])
                    if success:
                        self.get_all_files(force_refresh=True)
                        return f"✅ Successfully deleted '{result}'. The file has been removed from your directory."
                    else:
                        return f"❌ Failed to delete file: {result}"
                else:
                    return f"❌ File '{filename}' not found in the directory."
        
        # Build intelligent prompt for Gemini
        prompt = f"""
        You are a file system assistant. The user asked: "{query}"
        
        Here's the current directory information:
        {json.dumps(data, indent=2)}
        
        Please provide a natural, conversational response to their question.
        
        Guidelines:
        - If they ask about a specific file, provide detailed information
        - If they ask for the owner of a file, just mention the owner
        - If they ask when a file was created, just mention the creation time
        - If they ask to list files, provide a brief summary
        - If they ask about file types, categorize them
        - Be concise but helpful
        - Do not use markdown formatting like ** or * in your response
        - Speak naturally as if you're having a conversation
        
        Important: Always use the actual data provided above. Don't make up information.
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            st.error(f"Gemini API Error: {e}")
            # Fallback response
            return f"Error processing query. File count: {data['total_files']}"

class VoiceAssistant:
    def __init__(self, file_tool):
        self.file_tool = file_tool
        self.deepgram = deepgram
        
    def transcribe_audio(self, audio_path):
        """Transcribe audio using Deepgram v3/v4 - synchronous version"""
        try:
            with open(audio_path, 'rb') as audio_file:
                buffer_data = audio_file.read()
            
            payload = {"buffer": buffer_data}
            
            # Configure options
            options = PrerecordedOptions(
                model="nova-2",
                smart_format=True,
                punctuate=True,
                language="en-US"
            )
            
            # Transcribe using v3/v4 API
            response = self.deepgram.listen.rest.v("1").transcribe_file(payload, options)
            
            # Extract transcript
            transcript = response.results.channels[0].alternatives[0].transcript
            return transcript
            
        except Exception as e:
            st.error(f"Transcription error: {e}")
            return ""
    
    def text_to_speech(self, text):
        """Convert text to speech using Deepgram TTS"""
        try:
            # Clean text for speech
            text = self.file_tool.clean_text_for_speech(text)
            
            # Limit text length
            text = text[:500] if len(text) > 500 else text
            
            # Get selected voice model
            voice_model = st.session_state.get('voice_model', 'aura-asteria-en')
            
            # Configure TTS options
            options = SpeakOptions(
                model=voice_model,
                encoding="linear16",
                container="wav"
            )
            
            # Create the text payload
            payload = {"text": text}
            
            # Use the save method which is more reliable
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                filename = tmp_file.name
            
            response = self.deepgram.speak.rest.v("1").save(filename, payload, options)
            
            # Read the file back
            with open(filename, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(filename)  # Clean up
            return audio_data
                
        except Exception as e:
            st.error(f"Deepgram TTS Error: {e}")
            return None
    
    def record_audio(self, duration=5):
        """Record audio from microphone"""
        try:
            CHUNK = 1024
            FORMAT = pyaudio.paInt16
            CHANNELS = 1
            RATE = 16000
            
            p = pyaudio.PyAudio()
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            stream = p.open(format=FORMAT,
                           channels=CHANNELS,
                           rate=RATE,
                           input=True,
                           frames_per_buffer=CHUNK)
            
            frames = []
            
            for i in range(0, int(RATE / CHUNK * duration)):
                data = stream.read(CHUNK)
                frames.append(data)
                # Update progress
                progress = (i + 1) / int(RATE / CHUNK * duration)
                progress_bar.progress(progress)
                status_text.text(f"🎙️ Recording... {int(progress * 100)}%")
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Save audio
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
                wf = wave.open(tmp_file.name, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(p.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()
                return tmp_file.name
        except Exception as e:
            st.error(f"Recording error: {e}. Make sure your microphone is connected.")
            return None

def create_hello_world():
    """Create hello_world.txt file"""
    with open("hello_world.txt", "w") as f:
        f.write("Hello World! Created by AI Assistant\n")
        f.write(f"Timestamp: {datetime.now()}\n")
        f.write("This file was created as part of the AI File System Assistant demo.")
    return os.path.exists("hello_world.txt")

def create_custom_file(filename, content=""):
    """Create a custom file with specified name and content"""
    try:
        # Sanitize filename (remove potentially dangerous characters)
        safe_filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Add default extension if none provided
        if '.' not in safe_filename:
            safe_filename += '.txt'
        
        with open(safe_filename, "w") as f:
            if content:
                f.write(content)
            else:
                f.write(f"File created by AI Assistant\n")
                f.write(f"Filename: {safe_filename}\n")
                f.write(f"Created: {datetime.now()}\n")
                f.write(f"This file was created through the AI File System Assistant.")
        
        return True, safe_filename
    except Exception as e:
        return False, str(e)

def delete_file(filename):
    """Delete a file safely"""
    try:
        if os.path.exists(filename):
            # Don't delete system files or the app itself
            protected_files = ['app.py', 'file_lister.c', 'file_lister.exe', 
                             'requirements.txt', '.env', 'setup.bat']
            if filename.lower() in [f.lower() for f in protected_files]:
                return False, "Cannot delete protected system files"
            
            os.remove(filename)
            return True, filename
        else:
            return False, "File not found"
    except Exception as e:
        return False, str(e)

def main():
    st.set_page_config(page_title="AI File Assistant", page_icon="🤖", layout="wide")
    
    # Custom CSS for animations
    st.markdown("""
    <style>
    .stAlert {
        animation: fadeIn 0.5s;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'file_tool' not in st.session_state:
        st.session_state.file_tool = SmartFileSystemTool()
    if 'voice_assistant' not in st.session_state:
        st.session_state.voice_assistant = VoiceAssistant(st.session_state.file_tool)
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'audio_counter' not in st.session_state:
        st.session_state.audio_counter = 0
    if 'file_content' not in st.session_state:
        st.session_state.file_content = ""
    
    # Header
    st.title("🤖 Intelligent File System Assistant")
    st.markdown("*Ask me anything about your files - I understand natural language!*")
    
    # API Status indicator in sidebar
    with st.sidebar:
        st.header("🛠️ Controls")
        
        # Show API status
        with st.expander("🔌 API Status"):
            st.success("✅ Gemini: gemini-2.0-flash-001")
            st.success("✅ Deepgram STT: Connected")
            st.success("✅ Deepgram TTS: Connected")
        
        # Voice settings
        with st.expander("🎙️ Voice Settings"):
            # Voice models with descriptions
            voice_options = {
                "aura-asteria-en": "Asteria (Female, American)",
                "aura-luna-en": "Luna (Female, American)", 
                "aura-stella-en": "Stella (Female, American)",
                "aura-athena-en": "Athena (Female, British)",
                "aura-hera-en": "Hera (Female, American)",
                "aura-orion-en": "Orion (Male, American)",
                "aura-arcas-en": "Arcas (Male, American)",
                "aura-perseus-en": "Perseus (Male, American)",
                "aura-angus-en": "Angus (Male, Irish)",
                "aura-orpheus-en": "Orpheus (Male, American)",
                "aura-helios-en": "Helios (Male, British)",
                "aura-zeus-en": "Zeus (Male, American)"
            }
            
            selected_voice = st.selectbox(
                "TTS Voice",
                options=list(voice_options.keys()),
                format_func=lambda x: voice_options[x],
                help="Choose Deepgram voice model"
            )
            st.session_state.voice_model = selected_voice
        
        # FILE CREATION SECTION
        with st.expander("📝 Create Custom File", expanded=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                custom_filename = st.text_input(
                    "Filename", 
                    placeholder="example.txt",
                    help="Enter filename with extension",
                    key="filename_input"
                )
            with col2:
                file_type = st.selectbox(
                    "Type",
                    [".txt", ".md", ".json", ".csv", ".py", ".js", ".html", ".css", "custom"],
                    key="filetype_select"
                )
            
            # Auto-append extension unless custom is selected
            if file_type != "custom" and custom_filename and not custom_filename.endswith(file_type):
                display_filename = custom_filename + file_type
            else:
                display_filename = custom_filename
            
            # Quick templates
            template = st.selectbox(
                "Quick Templates",
                ["Empty", "Hello World", "README", "Python Script", "HTML Page", "JSON Config"],
                key="template_select"
            )
            
            # Template definitions
            templates = {
                "Empty": "",
                "Hello World": "Hello World!\nThis file was created by AI File Assistant.",
                "README": "# Project Title\n\n## Description\nBrief description here.\n\n## Installation\n```bash\nnpm install\n```\n\n## Usage\nHow to use this project.",
                "Python Script": "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\n\"\"\"\nScript created by AI File Assistant\n\"\"\"\n\ndef main():\n    print('Hello from AI Assistant!')\n\nif __name__ == '__main__':\n    main()",
                "HTML Page": "<!DOCTYPE html>\n<html lang='en'>\n<head>\n    <meta charset='UTF-8'>\n    <title>AI Generated Page</title>\n</head>\n<body>\n    <h1>Welcome!</h1>\n    <p>This page was created by AI File Assistant.</p>\n</body>\n</html>",
                "JSON Config": "{\n  \"name\": \"ai-project\",\n  \"version\": \"1.0.0\",\n  \"description\": \"Created by AI Assistant\",\n  \"author\": \"AI File System\",\n  \"created\": \"" + str(datetime.now()) + "\"\n}"
            }
            
            # Apply template button
            if st.button("🎯 Apply Template", use_container_width=True):
                st.session_state.file_content = templates.get(template, "")
                st.rerun() 
            
            # Content input - now uses session state
            file_content = st.text_area(
                "Content (optional)",
                value=st.session_state.file_content,
                placeholder="Enter file content here...",
                height=150,
                key="content_area"
            )
            
            # Update session state when content changes
            st.session_state.file_content = file_content
            
            # Create file button
            if st.button("✨ Create File", type="primary", use_container_width=True):
                if display_filename:
                    success, result = create_custom_file(display_filename, file_content)
                    if success:
                        st.success(f"✅ Created: {result}")
                        st.balloons()  # Keep the balloons
                        # Clear the content area after successful creation
                        st.session_state.file_content = ""
                        # Force refresh
                        st.session_state.file_tool.get_all_files(force_refresh=True)                    else:
                        st.error(f"❌ Error: {result}")
                else:
                    st.warning("Please enter a filename!")
        
        # Refresh files
        if st.button("🔄 Refresh Files", key="refresh", use_container_width=True):
            st.session_state.file_tool.get_all_files(force_refresh=True)
            st.success("✅ Files refreshed!")
        
        # Validate
        if st.button("🔍 Validate (dir /Q)", key="validate", use_container_width=True):
            result = subprocess.run(["cmd", "/c", "dir", "/Q"], capture_output=True, text=True)
            with st.expander("Windows dir output"):
                st.code(result.stdout)
        
        st.divider()
        
        # Example queries
        st.subheader("💡 Example Queries")
        examples = [
            "Create hello_world.txt",
            "Who owns hello_world.txt?",
            "When was hello_world.txt created?",
            "List all files",
            "Show me all text files",
            "Show me all Python files",
            "What's the largest file?",
            "How many files are there?",
            "Show files created today",
            "Create test.py with content: print('Hello')",
            "Delete old_file.txt"
        ]
        
        for example in examples:
            if st.button(example, key=f"ex_{example}", use_container_width=True):
                st.session_state.example_query = example
    
    # Main content
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "🎙️ Voice", "📊 File Explorer"])
    
    with tab1:
        # Check for example query
        if 'example_query' in st.session_state:
            query = st.session_state.example_query
            del st.session_state.example_query
            
            # Add to messages and process
            st.session_state.messages.append({"role": "user", "content": query})
            response = st.session_state.file_tool.query_files(query)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.rerun()
        
        # Display messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask anything about your files..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.write(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("🤔 Analyzing your files..."):
                    response = st.session_state.file_tool.query_files(prompt)
                    st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                    
                    # Generate voice response with Deepgram
                    with st.spinner("🔊 Generating audio with Deepgram..."):
                        audio = st.session_state.voice_assistant.text_to_speech(response)
                        if audio:
                            # Increment counter for unique key
                            st.session_state.audio_counter += 1
                            st.audio(audio, format='audio/wav')
    
    with tab2:
        st.subheader("🎙️ Voice Interface")
        st.info("📢 Using Deepgram for both speech-to-text and text-to-speech")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("### Quick Voice Commands")
            duration = st.slider("Recording duration (seconds)", 3, 10, 5)
            
            if st.button("🎤 Start Recording", type="primary", use_container_width=True):
                with st.container():
                    audio_path = st.session_state.voice_assistant.record_audio(duration)
                    if audio_path:
                        st.session_state.last_recording = audio_path
                        
                        # Auto-transcribe
                        with st.spinner("📝 Transcribing with Deepgram STT..."):
                            transcript = st.session_state.voice_assistant.transcribe_audio(audio_path)
                            if transcript:
                                st.session_state.last_transcript = transcript
                                
                                # Auto-process
                                with st.spinner("🤖 Processing with Gemini..."):
                                    response = st.session_state.file_tool.query_files(transcript)
                                    st.session_state.last_voice_response = response
                                
                                # Generate audio response with Deepgram TTS
                                with st.spinner("🔊 Generating audio with Deepgram TTS..."):
                                    audio = st.session_state.voice_assistant.text_to_speech(response)
                                    st.session_state.last_audio_response = audio
                            else:
                                st.error("No transcript received. Please try again.")
        
        with col2:
            if hasattr(st.session_state, 'last_transcript'):
                st.markdown("### 🎯 Conversation")
                
                # User query
                st.info(f"**You said:** {st.session_state.last_transcript}")
                
                # AI response
                if hasattr(st.session_state, 'last_voice_response'):
                    st.success(f"**AI Response:** {st.session_state.last_voice_response}")
                    
                    # Audio player
                    if hasattr(st.session_state, 'last_audio_response') and st.session_state.last_audio_response:
                        st.session_state.audio_counter += 1
                        st.audio(st.session_state.last_audio_response, format='audio/wav')
    
    with tab3:
        st.subheader("📁 File Explorer")
        
        # Get files
        data = st.session_state.file_tool.get_all_files()
        
        if data['files']:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Files", data['total_files'])
            
            with col2:
                dirs = sum(1 for f in data['files'] if f['type'] == 'directory')
                st.metric("Directories", dirs)
            
            with col3:
                files = sum(1 for f in data['files'] if f['type'] == 'file')
                st.metric("Regular Files", files)
            
            with col4:
                hidden = sum(1 for f in data['files'] if f['attributes']['hidden'])
                st.metric("Hidden Items", hidden)
            
            # File table
            st.markdown("### 📋 Detailed File List")
            
            # Convert to DataFrame
            df_data = []
            for file in data['files']:
                df_data.append({
                    'Name': file['name'],
                    'Type': file['type'],
                    'Size': f"{file['size']:,}" if file['type'] == 'file' else 'N/A',
                    'Owner': file['owner'].split('\\')[-1],
                    'Created': file['created'],
                    'Modified': file['modified'],
                    'Hidden': '🔒' if file['attributes']['hidden'] else '',
                    'ReadOnly': '📝' if file['attributes']['readonly'] else ''
                })
            
            df = pd.DataFrame(df_data)
            
            # Highlight hello_world.txt if it exists
            def highlight_target(row):
                if row['Name'] == 'hello_world.txt':
                    return ['background-color: #90EE90'] * len(row)
                return [''] * len(row)
            
            styled_df = df.style.apply(highlight_target, axis=1)
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            st.warning("No files found in current directory")

if __name__ == "__main__":
    main()