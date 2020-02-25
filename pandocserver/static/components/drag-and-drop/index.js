export default class DragAndDrop {
  constructor(el) {
    this.el = el;
  }

  render() {
    this.el.innerHTML = `
      <div id="drop-area">
        <form class="my-form" enctype="multipart/form-data" accept-charset="UTF-8">
          <div><h1>Convert</h1>
          <label for="fromElem">from</label>
          <select class="select-css" id="fromElem">
            <option value="commonmark">CommonMark</option>
            <option value="creole">Creole</option>
            <option value="docbook">DocBook</option>
            <option value="dokuwiki">DokuWiki</option>
            <option value="fb2">FB2</option>
            <option value="haddock">Haddock markup</option>
            <option value="html">HTML</option>
            <option value="jats">JATS</option>
            <option value="ipynb">Jupyter Notebook (ipynb)</option>
            <option value="latex">LaTeX</option>
            <option value="man">Man</option>
            <option value="markdown" selected>Markdown (pandoc)</option>
            <option value="gfm">Markdown (GitHub-flavored)</option>
            <option value="markdown_phpextra">Markdown (PHP Markdown Extra)</option>
            <option value="markdown_strict">Markdown (strict)</option>
            <option value="mediawiki">MediaWiki</option>
            <option value="markdown_mmd">MultiMarkdown</option>
            <option value="muse">Muse</option>
            <option value="native">Native (Pandoc AST)</option>
            <option value="opml">OPML</option>
            <option value="org">Org Mode</option>
            <option value="rst">reStructuredText</option>
            <option value="t2t">Txt2Tags</option>
            <option value="textile">Textile</option>
            <option value="tikiwiki">TikiWiki</option>
            <option value="twiki">TWiki</option>
            <option value="vimwiki">Vimwiki</option>
          </select>
          </div>
          <div>
          <label for="toElem">to</label>
          <select class="select-css" id="toElem">
            <option value="S5">S5</option>
            <option value="asciidoc">AsciiDoc (original)</option>
            <option value="asciidoctor">AsciiDoc (asciidoctor-flavored)</option>
            <option value="beamer">LaTeX Beamer</option>
            <option value="commonmark">CommonMark</option>
            <option value="context">ConTeXt</option>
            <option value="docbook4">DocBook v4</option>
            <option value="docbook5">DocBook v5</option>
            <option value="dokuwiki">DokuWiki</option>
            <option value="dzslides">DZSlides</option>
            <option value="haddock">Haddock markup</option>
            <option value="html4">HTML 4</option>
            <option value="html5">HTML 5</option>
            <option value="icml">ICML</option>
            <option value="jats">JATS</option>
            <option value="json">JSON</option>
            <option value="ipynb">Jupyter Notebook (ipynb)</option>
            <option value="latex">LaTeX</option>
            <option value="man">Man</option>
            <option value="ms">Ms</option>
            <option value="markdown" selected>Markdown (pandoc)</option>
            <option value="gfm">Markdown (GitHub-flavored)</option>
            <option value="markdown_phpextra">Markdown (PHP Markdown Extra)</option>
            <option value="markdown_strict">Markdown (strict)</option>
            <option value="mediawiki">MediaWiki</option>
            <option value="markdown_mmd">MultiMarkdown</option>
            <option value="muse">Muse</option>
            <option value="native">Native (Pandoc AST)</option>
            <option value="opendocument">OpenDocument</option>
            <option value="opml">OPML</option>
            <option value="org">Org Mode</option>
            <option value="pdf" selected>PDF</option>
            <option value="plain">Plain text</option>
            <option value="revealjs">reveal.js</option>
            <option value="rst">reStructuredText</option>
            <option value="rtf">RTF</option>
            <option value="slideous">Slideous</option>
            <option value="slidy">Slidy</option>
            <option value="tei">TEI</option>
            <option value="texinfo">Texinfo</option>
            <option value="textile">Textile</option>
            <option value="zimwiki">ZimWiki</option>
          </select>
          </div>
          <p>Upload multiple image or other files with the file dialog or by dragging and dropping images on the dashed line</p>
          <input type="file" id="fileElem" multiple accept="file_extension">
          <label class="button" for="fileElem">Add more files</label>  
        </form>
        <progress id="progress-bar" max="100" value="10"></progress>
        <div id="gallery"></div>
      </div>
    `;
  }

  init() {
    const dropArea = this.el.querySelector("#drop-area");
    const progressBar = this.el.querySelector("#progress-bar");
    const fileElem = this.el.querySelector("#fileElem");
    const fromElem = this.el.querySelector("#fromElem");
    const toElem = this.el.querySelector("#toElem");
    const gallery = this.el.querySelector("#gallery");
    const postUrl = this.el.dataset.postUrl;
    let uploadProgress = [];

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    function highlight() {
      dropArea.classList.add("highlight");
    }

    function unHighlight() {
      dropArea.classList.remove("active");
    }

    dropArea.addEventListener("drop", handleDrop, false);
    fileElem.addEventListener("change", handleFiles.bind(fileElem.files));

    ["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
      dropArea.addEventListener(eventName, preventDefaults, false);
    });

    ["dragenter", "dragover"].forEach(eventName => {
      dropArea.addEventListener(eventName, highlight, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
      dropArea.addEventListener(eventName, unHighlight, false);
    });

    function handleDrop(e) {
      const dt = e.dataTransfer;
      let files = dt.files;
      files = [...files];
      initializeProgress(files.length);
      files.forEach(uploadFile);
      files.forEach(previewFile);
    }

    function initializeProgress(numFiles) {
      progressBar.value = 0;
      uploadProgress = [];
      for (let i = numFiles; i > 0; i--) {
        uploadProgress.push(0);
      }
    }

    function updateProgress(fileNumber, percent) {
      uploadProgress[fileNumber] = percent;
      let total =
        uploadProgress.reduce((tot, curr) => tot + curr, 0) /
        uploadProgress.length;
      console.debug("update", fileNumber, percent, total);
      progressBar.value = total;
    }

    function handleFiles(files) {
      files = [...files.target.files];
      initializeProgress(files.length);
      files.forEach(uploadFile);
      files.forEach(previewFile);
    }

    function previewFile(file) {
      let reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onloadend = () => {
        if (
          file.type === "image/jpeg" ||
          file.type === "image/png" ||
          file.type === "image/gif"
        ) {
          const img = document.createElement("img");
          img.src = reader.result;
          gallery.appendChild(img);
        } else {
          const doc = document.createElement("img");
          doc.src = "./static/assets/img/document.png";
          gallery.appendChild(doc);
        }
      };
    }

    function download(data, strFileName, strMimeType) {

      let self = window, // this script is only for browsers anyway...
          defaultMime = "application/octet-stream", // this default mime also triggers iframe downloads
          mimeType = strMimeType || defaultMime,
          payload = data,
          url = !strFileName && !strMimeType && payload,
          anchor = document.createElement("a"),
          toString = function(a){return String(a);},
          myBlob = (self.Blob || self.MozBlob || self.WebKitBlob || toString),
          fileName = strFileName || "download",
          blob,
          reader;
      myBlob= myBlob.call ? myBlob.bind(self) : Blob ;

      if(String(this)==="true"){ //reverse arguments, allowing download.bind(true, "text/xml", "export.xml") to act as a callback
        payload=[payload, mimeType];
        mimeType=payload[0];
        payload=payload[1];
      }


      if(url && url.length< 2048){ // if no filename and no mime, assume a url was passed as the only argument
        fileName = url.split("/").pop().split("?")[0];
        anchor.href = url; // assign href prop to temp anchor
        if(anchor.href.indexOf(url) !== -1){ // if the browser determines that it's a potentially valid url path:
          let ajax=new XMLHttpRequest();
          ajax.open( "GET", url, true);
          ajax.responseType = 'blob';
          ajax.onload= function(e){
            download(e.target.response, fileName, defaultMime);
          };
          setTimeout(function(){ ajax.send();}, 0); // allows setting custom ajax headers using the return:
          return ajax;
        } // end if valid url?
      } // end if url?


      //go ahead and download dataURLs right away
      if(/^data\:[\w+\-]+\/[\w+\-]+[,;]/.test(payload)){

        if(payload.length > (1024*1024*1.999) && myBlob !== toString ){
          payload=dataUrlToBlob(payload);
          mimeType=payload.type || defaultMime;
        }else{
          return navigator.msSaveBlob ?  // IE10 can't do a[download], only Blobs:
              navigator.msSaveBlob(dataUrlToBlob(payload), fileName) :
              saver(payload) ; // everyone else can save dataURLs un-processed
        }

      }//end if dataURL passed?

      blob = payload instanceof myBlob ?
          payload :
          new myBlob([payload], {type: mimeType}) ;


      function dataUrlToBlob(strUrl) {
        let parts= strUrl.split(/[:;,]/),
            type= parts[1],
            decoder= parts[2] == "base64" ? atob : decodeURIComponent,
            binData= decoder( parts.pop() ),
            mx= binData.length,
            i= 0,
            uiArr= new Uint8Array(mx);

        for(i;i<mx;++i) uiArr[i]= binData.charCodeAt(i);

        return new myBlob([uiArr], {type: type});
      }

      function saver(url, winMode){

        if ('download' in anchor) { //html5 A[download]
          anchor.href = url;
          anchor.setAttribute("download", fileName);
          anchor.className = "download-js-link";
          anchor.innerHTML = "downloading...";
          anchor.style.display = "none";
          document.body.appendChild(anchor);
          setTimeout(function() {
            anchor.click();
            document.body.removeChild(anchor);
            if(winMode===true){setTimeout(function(){ self.URL.revokeObjectURL(anchor.href);}, 250 );}
          }, 66);
          return true;
        }

        // handle non-a[download] safari as best we can:
        if(/(Version)\/(\d+)\.(\d+)(?:\.(\d+))?.*Safari\//.test(navigator.userAgent)) {
          url=url.replace(/^data:([\w\/\-\+]+)/, defaultMime);
          if(!window.open(url)){ // popup blocked, offer direct download:
            if(confirm("Displaying New Document\n\nUse Save As... to download, then click back to return to this page.")){ location.href=url; }
          }
          return true;
        }

        //do iframe dataURL download (old ch+FF):
        let f = document.createElement("iframe");
        document.body.appendChild(f);

        if(!winMode){ // force a mime that will download:
          url="data:"+url.replace(/^data:([\w\/\-\+]+)/, defaultMime);
        }
        f.src=url;
        setTimeout(function(){ document.body.removeChild(f); }, 333);

      }//end saver

      if (navigator.msSaveBlob) { // IE10+ : (has Blob, but not a[download] or URL)
        return navigator.msSaveBlob(blob, fileName);
      }

      if(self.URL){ // simple fast and modern way using Blob and URL:
        saver(self.URL.createObjectURL(blob), true);
      }else{
        // handle non-Blob()+non-URL browsers:
        if(typeof blob === "string" || blob.constructor===toString ){
          try{
            return saver( "data:" +  mimeType   + ";base64,"  +  self.btoa(blob)  );
          }catch(y){
            return saver( "data:" +  mimeType   + "," + encodeURIComponent(blob)  );
          }
        }

        // Blob but not URL support:
        reader=new FileReader();
        reader.onload=function(e){
          saver(this.result);
        };
        reader.readAsDataURL(blob);
      }
      return true;
    }; /* end download() */

    function uploadFile(file, i) {
      let url = postUrl;
      let formData = new FormData();
      let fileName = 'download';
      formData.append("from",fromElem.value);
      formData.append("to",toElem.value);
      formData.append("file", file);
      fetch(url, {
        method: "POST",
        body: formData,
        headers: {
          "Content-Encoding": "UTF-8"
        }
      }).then((response) => {
          updateProgress(i, 100);
          if(response.ok) {
            return response;
          }
          throw new Error('Network response was not ok.');
        })
        .then((response) => {
          fileName = response.headers.get('Content-Disposition').match(/filename="(.+)"/)[1];
          return response.blob();
        })
        .then((data) => {
           download(data, fileName, data.type)
        })
        .catch((error) => {
          console.error(
              'There has been a problem with your fetch operation: ', error.message
          );
        });
    }
  }

  run() {
    this.render();
    this.init();
  }
}
