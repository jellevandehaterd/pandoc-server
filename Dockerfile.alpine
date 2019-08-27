ARG cache=/opt/cache
FROM alpine as emoji-image

#
# Add local cache/. It's empty by default so this does not change the final
# image on Docker Hub.
#
# However, once warmed with make warm-cache, it can save a lots of bandwidth.
#
ARG cache
ENV CACHE=$cache
COPY cache/ ${CACHE}/

RUN apk add --no-cache librsvg \
 && [[ -f ${CACHE}/twemoji.tar.gz ]] || wget https://github.com/twitter/twemoji/archive/gh-pages.tar.gz -O ${CACHE}/twemoji.tar.gz \
 && mkdir -p /tmp/twemoji \
 && tar --strip-components 1 -zvxf ${CACHE}/twemoji.tar.gz -C /tmp/twemoji \
 && [[ -f ${CACHE}/xelatex-emoji.tar.gz ]] || wget https://github.com/mreq/xelatex-emoji/archive/master.tar.gz -O ${CACHE}/xelatex-emoji.tar.gz \
 && mkdir -p /tmp/xelatex-emoji/images \
 && tar --strip-components 1 -zvxf ${CACHE}/xelatex-emoji.tar.gz -C /tmp/xelatex-emoji \
 && cd /tmp/twemoji/2/svg \
 && . /tmp/xelatex-emoji/bin/convert_svgs_to_pdfs ./*.svg \
 && mv /tmp/twemoji/2/svg/*.pdf /tmp/xelatex-emoji/images/

FROM python:3.7-alpine as compile-image

ARG cache
ENV CACHE=$cache \
    PATH="/opt/venv/bin:$PATH"
COPY cache/ ${CACHE}/

WORKDIR /app
COPY requirements/*.txt ./
ADD dist/pandocserver-*.tar.gz ./

RUN apk add --no-cache \
            gcc \
            g++ \
            musl-dev \
            libffi-dev \
 && python3 -m venv /opt/venv

RUN $(which python) -m pip install \
        --no-cache-dir \
        --find-links file://${CACHE} \
        --requirement ./production.txt \
        ./pandocserver-* \
        --requirement ./pandoc_filters.txt \
    && $(which python) -m pip list

FROM pandoc/latex

ENV LANG=C.UTF-8 \
    APP_ROOT=/opt/app-root \
    USER_NAME=pandoc \
    UID=10001 \
    GID=10001

COPY --from=emoji-image /tmp/xelatex-emoji /opt/texlive/texmf-local/tex/latex/
ENV PATH=${APP_ROOT}/bin:${PATH} \
    HOME=${APP_ROOT}
COPY bin/ ${APP_ROOT}/bin/

RUN apk add --no-cache --repository=http://dl-cdn.alpinelinux.org/alpine/edge/main \
        texlive \
        texlive-luatex \
        texlive-xetex \
        texmf-dist-pstricks \
        xz \
        python3 \
 && chmod -R u+x ${APP_ROOT}/bin \
 && chgrp -R 0 ${APP_ROOT} \
 && chmod -R g=u ${APP_ROOT} /etc/passwd

COPY --from=compile-image /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:${PATH}
RUN ln -s /usr/bin/python3 /usr/local/bin/python3 \
 && python -m pip list \
 && python -m pip install pandoc-include

#
# eisvogel template
#
ARG TEMPLATES_DIR=${APP_ROOT}/.pandoc/templates
RUN mkdir -p ${TEMPLATES_DIR} && \
    wget https://raw.githubusercontent.com/Wandmalfarbe/pandoc-latex-template/master/eisvogel.tex -O ${TEMPLATES_DIR}/eisvogel.latex
RUN tlmgr update --self \
 && tlmgr init-usertree \
 && tlmgr install \
        ly1 \
        inconsolata \
        sourcesanspro \
        sourcecodepro \
        mweights \
        noto \
        needspace \
        mdframed \
        titling \
        adjustbox \
        collectbox \
        pagecolor \
 && texhash \
 && rm /opt/texlive/*/texmf-var/web2c/tlmgr.log

USER ${UID}
WORKDIR ${APP_ROOT}

EXPOSE 8080

ENTRYPOINT [ "entrypoint", "python","-m","pandocserver"]
VOLUME ${APP_ROOT}/logs ${APP_ROOT}/data
CMD ["run"]
