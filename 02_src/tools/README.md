Итог: у вас есть готовый пакет для инженера:



&nbsp; 02\_src/tools/

&nbsp; ├── network\_diag\_replay.py       ← скрипт (standalone, никаких зависимостей от проекта)

&nbsp; └── diag\_prompts/

&nbsp;     ├── United\_Kingdom\_regulated\_market\_equity\_distinct\_pass1\_prompt.txt   (18 KB)

&nbsp;     ├── United\_Kingdom\_regulated\_market\_equity\_standard\_pass1\_prompt.txt   (29 KB)

&nbsp;     ├── Hong\_Kong\_regulated\_market\_bond\_standard\_pass1\_prompt.txt          (66 KB)

&nbsp;     ├── Hong\_Kong\_regulated\_market\_equity\_distinct\_pass1\_prompt.txt        (28 KB)

&nbsp;     └── Hong\_Kong\_regulated\_market\_equity\_standard\_pass1\_prompt.txt        (79 KB)



&nbsp; Инженеру нужно:

&nbsp; 1. pip install python-dotenv langchain-openai langchain-core

&nbsp; 2. Положить рядом .env с OPENAI\_API\_KEY (и OPENAI\_BASE\_URL если нужен)

&nbsp; 3. python network\_diag\_replay.py

