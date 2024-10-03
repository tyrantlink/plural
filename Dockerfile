FROM python:3.12

RUN groupadd -g 1000 -o plural
RUN useradd -m -u 1000 -g 1000 -o -s /bin/bash plural
USER plural

ENV SCOPE=${SCOPE}

ENV PATH /home/plural/.local/bin:$PATH

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -U -r requirements.txt


CMD ["bash", "-c", "python3.12 -u main.py $SCOPE"]