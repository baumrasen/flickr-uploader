Install the virtual environment:

py -3 -m venv .venv  
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.venv\scripts\activate

python -m pip install --upgrade pip
pip install flickrapi 
pip install portalocker
