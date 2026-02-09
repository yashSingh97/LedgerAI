import os
import time
from itertools import cycle
from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEYS = [
    os.getenv("V_GEMINI_PROJECT_1"),
    os.getenv("V_GEMINI_PROJECT_2"),
    os.getenv("V_GEMINI_PROJECT_3"),
    os.getenv("Y_GEMINI_PROJECT_1"),
    os.getenv("Y_GEMINI_PROJECT_2"),
    os.getenv("Y_GEMINI_PROJECT_3"),
    os.getenv("H_GEMINI_PROJECT_1"),
    os.getenv("H_GEMINI_PROJECT_2")
]
API_KEYS = [k for k in API_KEYS if k and k.strip() and k.strip() != "-"]

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
MAX_RETRY_DURATION = 20  # seconds

print(f"[LLM] Loaded {len(API_KEYS)} API keys")


def should_retry_error(code: int) -> bool:
    return code in [429, 500, 503, 504]


def llm_call(prompt: str):
    """
    Returns:
        (response_text, None) on success
        (None, error_entry) on failure
    """
    if not API_KEYS:
        return None, {
            "type": "error",
            "source": "llm",
            "message": " 0 API Keys found. AI service is not configured correctly.",
            "fatal": True
        }

    key_cycle = cycle(enumerate(API_KEYS, start=1))
    start_time = time.time()
    attempt_count = 0
    error_log = []

    while (time.time() - start_time) < MAX_RETRY_DURATION:
        attempt_count += 1
        key_num, api_key = next(key_cycle)

        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            print(f"[LLM] Success with API key #{key_num} (attempt {attempt_count})")
            return response.text, None

        except Exception as e:
            error_code = getattr(e, "code", None)
            error_message = getattr(e, "message", str(e))

            error_log.append({
                "key_num": key_num,
                "attempt": attempt_count,
                "code": error_code,
                "message": error_message
            })

            print(f"[LLM] Key #{key_num} failed - Code: {error_code}, Message: {error_message}")

            if error_code and should_retry_error(error_code):
                time.sleep(1)
                continue

            # Non-retryable → stop immediately
            return None, {
                "type": "error",
                "source": "llm",
                "message": "The AI engine failed to process your request with unknown non-retryable reason.",
                "fatal": True
            }

    # Retry window exhausted
    print(f"[LLM] Max retry duration exceeded. Attempts: {attempt_count}")
    print(f"[LLM] Error log: {error_log}")

    return None, {
        "type": "error",
        "source": "llm",
        "message": f"All {len(API_KEYS)} API Keys are exhausted within the RETRY WINDOW of {MAX_RETRY_DURATION} seconds. AI engine is temporarily unavailable.",
        "fatal": True
    }


# import os
# import time
# from itertools import cycle
# from dotenv import load_dotenv
# from google import genai

# load_dotenv()

# # Load all API keys (filter out empty and "-")
# API_KEYS = [
#     os.getenv("V_GEMINI_PROJECT_1"),
#     os.getenv("V_GEMINI_PROJECT_2"),
#     os.getenv("V_GEMINI_PROJECT_3"),
#     os.getenv("Y_GEMINI_PROJECT_1"),
#     os.getenv("Y_GEMINI_PROJECT_2"),
#     os.getenv("Y_GEMINI_PROJECT_3"),
#     os.getenv("H_GEMINI_PROJECT_1"),
#     os.getenv("H_GEMINI_PROJECT_2"),
# ]
# API_KEYS = [k for k in API_KEYS if k and k.strip() and k.strip() != "-"]

# if not API_KEYS:
#     raise RuntimeError("No valid API keys found in .env")

# MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
# MAX_RETRY_DURATION = 150  # seconds

# print(f"[LLM] Loaded {len(API_KEYS)} API keys")

# def should_retry_error(code: int) -> bool:
#     """
#     Check if error code indicates we should retry with another key.
#     Only retry on quota/rate limit and temporary server errors.
#     """
#     # 429 - Rate limit / quota exhausted
#     # 500 - Internal server error
#     # 503 - Service unavailable
#     # 504 - Timeout
#     return code in [429, 500, 503, 504]


# def llm_call(prompt: str) -> str:
#     """
#     Make LLM call with circular API key rotation.
#     Keeps trying different keys for up to 150 seconds.
#     """
#     key_cycle = cycle(enumerate(API_KEYS, start=1))
    
#     start_time = time.time()
#     error_log = []
#     attempt_count = 0
    
#     while (time.time() - start_time) < MAX_RETRY_DURATION:
#         attempt_count += 1
#         key_num, api_key = next(key_cycle)
        
#         try:
#             client = genai.Client(api_key=api_key)
#             response = client.models.generate_content(
#                 model=MODEL,
#                 contents=prompt
#             )
            
#             # Success!
#             print(f"[LLM] Success with API key #{key_num} (attempt {attempt_count})")
#             if error_log:
#                 print(f"[LLM] Previous errors: {error_log}")
            
#             return response.text
            
#         except Exception as e:
#             error_code = e.code if hasattr(e, 'code') else None
#             error_message = e.message if hasattr(e, 'message') else str(e)
            
#             error_log.append({
#                 "key_num": key_num,
#                 "attempt": attempt_count,
#                 "code": error_code,
#                 "message": error_message
#             })
            
#             print(f"[LLM] Key #{key_num} failed - Code: {error_code}, Message: {error_message}")
            
#             # Check if we should retry
#             if error_code and should_retry_error(error_code):
#                 elapsed = time.time() - start_time
#                 print(f"[LLM] Retrying with next key... (elapsed: {elapsed:.1f}s)")
#                 time.sleep(1)  # Small delay before retry
#                 continue
#             else:
#                 # Non-retryable error - propagate immediately
#                 print(f"[LLM] Non-retryable error. Error log: {error_log}")
#                 raise e
    
#     # Time limit exceeded
#     print(f"[LLM] Max retry duration ({MAX_RETRY_DURATION}s) exceeded")
#     print(f"[LLM] Total attempts: {attempt_count}")
#     print(f"[LLM] Error log: {error_log}")
    
#     # Raise exception with full error details
#     if error_log:
#         last_error = error_log[-1]
#         raise Exception (
#             f"""All retries exhausted. Tried {attempt_count} attempts across {len(API_KEYS)} keys. 
#             Last error (Key #{last_error['key_num']}): Code {last_error['code']} - {last_error['message']}"""
#         )
        
#     return "[LLM] I'm sorry, but I couldn't generate a response."