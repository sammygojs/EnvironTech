Command to install and run project.

#For Windows. Please find the steps at the end for mac.

python -m pip install --upgrade pip
python -m pip --version
python -m pip install virtualenv
python -m venv venv
venv/Scripts/Activate
pip install -r requirements.txt
python main.py


STEP 1
Install pip(dependency manager)
python -m pip install --upgrade pip
python -m pip --version

STEP 2
Install virtualenv(to isolate the versioning of the dependencies so they don't clash with global variables)
python -m pip install --user virtualenv

STEP 3
Create a virtual environment
python -m venv venv

STEP 4
activating virtual environment
venv/Scripts/Activate

STEP 5
Installing dependencies in virtual environment
pip install -r requirements.txt

STEP 6
Run the server
python main.py

MACINTOSH
python3 -m pip install --upgrade pip

python3 -m pip install --user virtualenv

python3 -m venv venv

. venv/bin/activate

pip install -r requirements.txt

python3 main.py

#These are steps for running on windows PC, please use python3 for macintosh or connect with me shdakoliya1@sheffield.ac.uk

--------------------------------------------------------
Issues you might face
Sometimes, we cant install pip in the virtual env, then we need to run pip via python using the following command
python -m pip install -r mysqlclient


Credentials
User 1: email: john1.doe@example.com password: 123
User 2: email: jane.smith@example.com password: 123

Admin: email: admin@example.com password:admin

Staff 1: email: staff@example.com password:staff

--------------------------------------------------------
Testing for stripe
Card numbers can be found at https://docs.stripe.com/testing#cards
