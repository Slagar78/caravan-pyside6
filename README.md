# Caravan (PySide6 port)

My attempt to port the Shining Force 2 editor [Caravan](https://github.com/ShiningForceCentral/Caravan) to **Python 3** and **PySide6**.

Original author: **BNC** ([chroipahtz](https://github.com/chroipahtz))  
Original repository: [ShiningForceCentral/Caravan](https://github.com/ShiningForceCentral/Caravan)

# Caravan BUILD ---\dist\Caravan.exe
pyinstaller --onefile --windowed --clean --noconfirm ^
    --name "Caravan" ^
    --icon=ico/caravan.ico ^
    --add-data "caravan.cfg;." ^
    --add-data "68k.xml;." ^
    --add-data "ico;ico" ^
    --add-data "panels;panels" ^
    caravan.py
	
# Caravan BUILD ---\dist\Caravan.exe	
	
	pyinstaller --onefile --windowed --clean --noconfirm ^
    --name "Caravan" ^
    --icon=ico/caravan.ico ^
    --add-data "caravan.cfg;." ^
    --add-data "68k.xml;." ^
    --add-data "ico;ico" ^
    --add-data "panels;panels" ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    caravan.py