for /D %%G in (data\raw\*) do (
    for %%f in (data\raw\%%~nxG\*) do pdftotext %%f
    mkdir data\text\%%~nxG
    for %%f in (data\raw\%%~nxG\*txt) do move %%f data\text\%%~nxG\
)