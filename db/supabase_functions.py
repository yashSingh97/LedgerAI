from typing import List, Dict, Optional
from db.init_client import supabase


def create_new_chat(title: str = "New Chat!") -> Optional[str]:
    """
    Create a new chat session.
    Returns chat_id if successful, None otherwise.
    """
    try:
        response = supabase.table("chats").insert({
            "title": title
        }).execute()
        print("Supabase response:", response)
        if response.data:
            chat_id = response.data[0]["chat_id"]
            print(f"[Supabase] Created new chat: {chat_id}")
            return chat_id
        return None
    except Exception as e:
        print(f"[Supabase] Error creating chat: {e}")
        return None


def update_chat_title(chat_id: str, title: str) -> bool:
    """
    Update the title of an existing chat.
    """
    try:
        supabase.table("chats").update({
            "title": title,
        }).eq("chat_id", chat_id).execute()
        print(f"[Supabase] Updated chat title: {chat_id}")
        return True
    except Exception as e:
        print(f"[Supabase] Error updating chat title: {e}")
        return False


def add_message(chat_id: str, role: str, content: str) -> bool:
    """
    Add a message to a chat.
    role should be 'user' or 'assistant'
    """
    try:
        supabase.table("chat_messages").insert({
            "chat_id": chat_id,
            "role": role,
            "content": content
        }).execute()
        
        # # Update the chat's updated_at timestamp
        # supabase.table("chats").update({
        #     "updated_at": "NOW()"
        # }).eq("chat_id", chat_id).execute()
        
        return True
    except Exception as e:
        print(f"[Supabase] Error adding message: {e}")
        return False


def get_chat_messages(chat_id: str) -> List[Dict]:
    """
    Get all messages for a specific chat.
    Returns list of messages sorted by created_at.
    """
    try:
        response = supabase.table("chat_messages")\
            .select("*")\
            .eq("chat_id", chat_id)\
            .order("created_at", desc=False)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"[Supabase] Error fetching messages: {e}")
        return []


def get_all_chats() -> List[Dict]:
    """
    Get all chats, sorted by most recently updated.
    """
    try:
        response = supabase.table("chats")\
            .select("*")\
            .order("updated_at", desc=True)\
            .execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"[Supabase] Error fetching chats: {e}")
        return []


def delete_chat(chat_id: str) -> bool:
    """
    Delete a chat and all its messages (CASCADE).
    """
    try:
        supabase.table("chats").delete().eq("chat_id", chat_id).execute()
        print(f"[Supabase] Deleted chat: {chat_id}")
        return True
    except Exception as e:
        print(f"[Supabase] Error deleting chat: {e}")
        return False


def generate_chat_title(first_message: str) -> str:
    """
    Generate a simple title from the first user message.
    Takes first 50 characters or until first newline.
    """
    title = first_message.split('\n')[0][:50]
    return title if title else "New Chat"