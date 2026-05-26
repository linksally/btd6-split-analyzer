import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
