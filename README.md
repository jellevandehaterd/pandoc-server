# pandoc-server

A WSGI service that allow you to create pdf from markdown

# Installation

```
docker build .
```

# Usage

Launch:

```
docker run -it -p 8080:8080 ${container-id}
```

The service listens now the `:8080` port where you can POST data.

# POST Data

Eache value are sent as POST forma data:

- "m": markdown content or file
- "t": title that will be used to name the returned pdf file 

You should do:

```bash
$ tar -czvf ${outputfile} ${documentation-dir}
```

And you can now try:

```bash
curl -X POST \
    -F "m=@my-tar-of-documentation-directory" \ 
    -o out.tar.gz \
    ${http://server:port}
```

