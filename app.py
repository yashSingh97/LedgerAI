import streamlit as st 
from core.graph import build_graph
from datetime import datetime 
from db.supabase_functions import (
    create_new_chat, 
    add_message, 
    get_chat_messages, 
    get_all_chats, 
    delete_chat,
    update_chat_title,
    generate_chat_title
)

# ==== PAGE CONFIG ====
st.set_page_config(page_title="LedgerAI", page_icon="🤖", layout="wide")

# ==== INITIALIZE AGENT ====
if 'app' not in st.session_state:
    st.session_state.app = build_graph()
    print("[Streamlit] Agent initialized.")

# ==== SESSION STATE INITIALIZATION ====
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'agent_state' not in st.session_state:
    today = datetime.now().strftime("%Y-%m-%d")
    st.session_state.agent_state = {
        "user_name": "User",
        "user_input": "",
        "long_term_memory": [],
        "short_term_memory": [],
        "today_date_context": today,
        "tasks": [],
        "tasks_count": 0,
        "current_task": None,
        "results": [],
        "route_to": None,
        "final_output": "",
        "should_continue": True
    }

# ==== HELPER FUNCTIONS ====
def load_chat(chat_id: str):
    """Load a chat from Supabase and update session state"""
    messages = get_chat_messages(chat_id)
    st.session_state.current_chat_id = chat_id
    st.session_state.messages = [
        {"role": msg["role"], "content": msg["content"]} 
        for msg in messages
    ]
    
    # Rebuild long_term_memory from loaded messages
    st.session_state.agent_state["long_term_memory"] = [
        {"role": "human" if msg["role"] == "user" else "assistant", "content": msg["content"]}
        for msg in messages
    ]
    
    # Rebuild short_term_memory (last 5 pairs = 10 messages)
    all_msgs = st.session_state.agent_state["long_term_memory"]
    st.session_state.agent_state["short_term_memory"] = all_msgs[-10:]


def start_new_chat():
    """Start a new chat session (doesn't create in DB yet)"""
    st.session_state.current_chat_id = None
    st.session_state.messages = []
    today = datetime.now().strftime("%Y-%m-%d")
    st.session_state.agent_state = {
        "user_name": "User",
        "user_input": "",
        "long_term_memory": [],
        "short_term_memory": [],
        "today_date_context": today,
        "tasks": [],
        "tasks_count": 0,
        "current_task": None,
        "results": [],
        "route_to": None,
        "final_output": "",
        "should_continue": True
    }


# ==== SIDEBAR ====
with st.sidebar:
    st.title("💬 Chat History")
    
    # New Chat button
    if st.button("➕ New Chat", use_container_width=True):
        start_new_chat()
        st.rerun()
    
    st.divider()
    
    # Load all chats
    chats = get_all_chats()
    
    if chats:
        for chat in chats:
            col1, col2 = st.columns([4, 1])
            
            with col1:
                # Highlight current chat
                is_current = st.session_state.current_chat_id == chat["chat_id"]
                button_label = f"{'📌 ' if is_current else ''}{chat['title']}"
                
                if st.button(button_label, key=chat["chat_id"], use_container_width=True):
                    load_chat(chat["chat_id"])
                    st.rerun()
            
            with col2:
                if st.button("🗑️", key=f"del_{chat['chat_id']}"):
                    delete_chat(chat["chat_id"])
                    if st.session_state.current_chat_id == chat["chat_id"]:
                        start_new_chat()
                    st.rerun()
    else:
        st.info("No chat history yet")

# ==== MAIN CHAT INTERFACE ====
st.title("🤖 Finance AI Assistant")
st.write("Ask about expenses, add transactions, or get predictions")

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # If this is the first message, create a new chat in Supabase
    if st.session_state.current_chat_id is None:
        title = generate_chat_title(prompt)
        chat_id = create_new_chat(title)
        
        if chat_id:
            st.session_state.current_chat_id = chat_id
            # Save the user message
            add_message(chat_id, "user", prompt)
        else:
            st.error("Failed to create chat. Please try again.")
            st.stop()
    else:
        # Save user message to existing chat
        add_message(st.session_state.current_chat_id, "user", prompt)
    
    # Prepare agent state
    state = st.session_state.agent_state
    state["user_input"] = prompt
    
    # Update long_term_memory
    state["long_term_memory"].append({"role": "human", "content": prompt})
    
    # Update short_term_memory (keep last 5 pairs = 10 messages)
    stm = state["short_term_memory"]
    stm.append({"role": "human", "content": prompt})
    state["short_term_memory"] = stm[-10:]
    
    # Run agent with spinner
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            final_state = st.session_state.app.invoke(state)
            response = final_state.get("final_output", "No response generated.")
            st.markdown(response)
    
    # Update chat history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Save assistant message to Supabase
    add_message(st.session_state.current_chat_id, "assistant", response)
    
    # Update long_term_memory
    state["long_term_memory"].append({"role": "assistant", "content": response})
    
    # Update short_term_memory (keep last 5 pairs = 10 messages)
    stm = state["short_term_memory"]
    stm.append({"role": "assistant", "content": response})
    state["short_term_memory"] = stm[-10:]
    
    # Reset state for next interaction (keep memories)
    st.session_state.agent_state = {
        "user_name": state["user_name"],
        "user_input": "",
        "long_term_memory": state["long_term_memory"],
        "short_term_memory": state["short_term_memory"],
        "today_date_context": state["today_date_context"],
        "tasks": [],
        "tasks_count": 0,
        "current_task": None,
        "results": [],
        "route_to": None,
        "final_output": "",
        "should_continue": True
    }
    
    st.rerun()