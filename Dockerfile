FROM python:3.13

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && npm install -g pnpm

RUN groupadd -g 1000 -o plural
RUN useradd -m -u 1000 -g 1000 -o -s /bin/bash plural

ENV PATH /home/plural/.local/bin:$PATH

WORKDIR /app

COPY . .

RUN pnpm i

USER plural

RUN pip install --no-cache-dir -U -r requirements.txt

CMD ["bash", "-c", "pnpm docs:build && python3.13 -u main.py"]
