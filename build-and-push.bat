@echo off
setlocal


:: Increment version in VERSION file
for /f "tokens=1-3 delims=." %%a in (VERSION) do (
    set major=%%a
    set minor=%%b
    set patch=%%c
)
set /a patch+=1
set new_version=%major%.%minor%.%patch%
echo %new_version% > VERSION

echo Updating setup.py with version %new_version%
python -c "import re; f=open('setup.py', 'r+'); content=f.read(); f.seek(0); f.write(re.sub(r'version=\"[0-9]+\.[0-9]+\.[0-9]+\"', f'version=\"%new_version%\"', content, count=1)); f.truncate(); f.close()"

:: Build and publish the package
echo Building the package...
python -m build

echo Publishing the package locally...
twine upload --repository-url http://10.10.0.12:8082/ dist/*
endlocal