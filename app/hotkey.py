""" Global hotkeys via the Win32 RegisterHOtKey API.( no global keyboard hook)
    
    One background thread owns the hotkeys: RegisterHotKey must run on the same
    thread as the message loop. because WM_HOTKEY is posted to that thread's queue.
    Other threads(e.g. the web setting handler) ask this thread to re-register by 
    posting WM_RELOAD stopping posts WM_QUIT.
"""

