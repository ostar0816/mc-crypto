FROM python:3.6
ADD . /shore
WORKDIR /shore
COPY docker-data/macchina_rsa /root/.ssh/id_rsa
COPY docker-data/macchina_rsa.pub /root/.ssh/id_rsa.pub
COPY docker-data/ssh_config /root/.ssh/config
RUN chmod 600 /root/.ssh/id_rsa
RUN eval $(ssh-agent -s) &&\
    ssh-add /root/.ssh/id_rsa
ENV DATABASE_HOST='localhost'
RUN pip install --no-cache-dir -r requirements.txt
RUN apt update && \
    curl -sL https://deb.nodesource.com/setup_9.x | bash -&& \
    apt-get install -y nodejs && \
    npm install webpack -g && \
    npm install webpack -D && \
    npm install webpack-cli -g && \
    npm install -D webpack-bundle-tracker && \
    npm --prefix /shore/shore install && \
    webpack --config shore/webpack_production.config.js && \
    webpack --stats-json --config shore/webpack.config.js && \
    mv webpack-stats.json shore/
