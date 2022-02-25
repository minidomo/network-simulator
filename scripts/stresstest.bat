for /l %%i IN (1000, 1, 1002) DO (
    echo Begin %%i
    START cmd /c python3 ../Thread/server %%i ^> %%i
    echo done
    for /l %%j IN (1000, 1, %%i) DO (
	echo started client %%i
        START cmd /c python3 ../Thread/client localhost %%i ^< readme.txt
    )
)