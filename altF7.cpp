#include <Windows.h>

extern "C" {
    void sendKeyPress();
}

void sendKeyPress()
{
    INPUT input[2];
	
	// https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
	// Нажатие клавиши Alt
    input[0].type = INPUT_KEYBOARD;
    input[0].ki.wVk = VK_MENU;
    input[0].ki.dwFlags = 0;

    // Нажатие клавиши F7
    input[1].type = INPUT_KEYBOARD;
    input[1].ki.wVk = VK_F7;
    input[1].ki.dwFlags = 0;
	
	SendInput(2, input, sizeof(INPUT));
 
    // Освобождение клавиши F7
    input[0].ki.dwFlags = KEYEVENTF_KEYUP;
 
    // Освобождение клавиши Alt
    input[1].ki.dwFlags = KEYEVENTF_KEYUP;
	
    SendInput(2, input, sizeof(INPUT));
}