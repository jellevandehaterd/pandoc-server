import logging
import os
import tarfile
import shutil
from cgi import FieldStorage
from subprocess import PIPE, Popen
from tempfile import mkstemp, mkdtemp


def pandoc(m, from_dir):
    ret = False
    tf, tp = mkstemp(suffix=".pdf")
    try:
        cmd = ["pandoc",
               "-f", "markdown",
               "-o", tp]
        cmd.insert(1, "--template")
        cmd.insert(2, "eisvogel")
        print("running command: %s" % cmd)
        p = Popen(cmd, cwd=from_dir, stdin=PIPE)
        p.stdin.write(m)
        p.stdin.close()
        p.wait()
        with open(tp,'r') as f:
            ret = f.read()
    except Exception, e:
        logging.exception(e)
        raise Exception(e)
    finally:
        try:
            os.remove(tp)
        except:
            pass

    print("--file converted")
    return ret

def set_cors(response_headers, environ):
    response_headers.append(('Access-Control-Allow-Methods', 'GET, POST, OPTIONS'))
    response_headers.append(('Access-Control-Allow-Origin', '*'))
    ach = environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', False)
    if ach:
        response_headers.append(('Access-Control-Allow-Headers', ach))


def extractFiles(file, to_dir):
    if file is not None and hasattr(file,'file'):
        os.chdir(to_dir)
        with tarfile.open(fileobj=file.file, mode='r:gz') as tgz:
            tgz.extractall('.')


def convertFiles(from_dir, to_dir):
    for subdir, _, files in os.walk(from_dir):
        for file in files:
            filename = os.path.join(subdir, file)
            if filename.endswith(".md"):
                print("found file %s" % filename)
                markdownFile = open(filename)
                markdown = markdownFile.read()
                pdf = pandoc(markdown,subdir)
                tmpFileDir = mkstemp(suffix=".pdf", dir=to_dir)
                print("Created file %s" % tmpFileDir[1])
                with open(tmpFileDir[1], "w") as file:
                    file.write(pdf)


def bundleFiles(output_dir):
    tar_file = os.path.join(output_dir,'output.tar.gz')
    print("creating file %s" % tar_file)
    with tarfile.open(tar_file, "w:gz") as tar_handle:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                print("adding file %s" % file)
                tar_handle.add(os.path.join(root, file))
    with open(tar_file, 'r') as file:
        tar = file.read()
    return tar


def cleanup(dirs):
    try:
        for dir in dirs:
            shutil.rmtree(dir)
    except Exception as e:
        print("Was unable to delete directories")
        print("Error: %s" % e.message)


def app(environ, start_response):
    post = FieldStorage(
        fp = environ['wsgi.input'],
        environ = environ,
        keep_blank_values = True)

    # Get post vars
    title = post['t'].value if 't' in post else 'pandoc_generated'
    m = post['m'] if 'm' in post else None
    if m is None:
        response_headers = [('Content-Type', 'text/plain')]
        set_cors(response_headers, environ)
        start_response('500 InternalServerError', response_headers)
        return ["You must provide content !"]

    try:
        temp_dir = mkdtemp()
        extractFiles(m, temp_dir)
        output_dir = mkdtemp()
        convertFiles(temp_dir, output_dir)
        tar = bundleFiles(output_dir)
        cleanup([output_dir, temp_dir])

        response_headers = [
            ('Content-Type', 'application/tar+gzip'),
            ('Content-Disposition', 'attachment; filename=' + title + '.tar.gz'),
            ('Content-Transfer-Encoding', 'binary')
        ]
        set_cors(response_headers, environ)
        start_response('200 OK', response_headers)
        return [tar]
    except Exception as e:
        print("Error: %s" % e.message)
        response_headers = [('Content-Type', 'text/plain')]
        set_cors(response_headers, environ)
        start_response('500 InternalServerError', response_headers)
        return ["Something went wrong...",e.message]


if __name__ == '__main__':
    print("Starting webserver..")
    try:
        from wsgiref.simple_server import make_server
        srv = make_server('', 8080, app)
        logging.info("Listening 8080")
        print("Listening on port 8080")
        srv.serve_forever()
    except Exception as e:
        print(e)