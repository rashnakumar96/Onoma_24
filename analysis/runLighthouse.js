'use strict';
const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');
const fs=require('fs');


function launchChromeAndRunLighthouse(url, opts,config = null) {
  return chromeLauncher.launch({chromeFlags: opts.chromeFlags}).then(chrome => {
    opts.port = chrome.port;
    
    return lighthouse(url, opts, config).then(results => {

        return chrome.kill().then(() => results.report)
    }).catch((err)=>{console.log("Lighthouse threw an error with the url ",url);
    });
    
  });
}

const opts = {
  chromeFlags: ['--headless'],
  onlyCategories: ['performance']
  // maxWaitForLoad:['45000']
};


function measureWebsitePerformance(i){
  if (i<topSites.length){
    var url="http://"+topSites[i]
    console.log(url)
    launchChromeAndRunLighthouse(url,opts).then(results => {
      if (!fs.existsSync("lighthouseResults/")){
        fs.mkdirSync("lighthouseResults/")
      }
      fs.writeFile('lighthouseResults/'+topSites[i]+'Lighthouse.json',results,(err)=>{
        if (err){
          console.log('Error in writting Data to file',err);
        }
        else{
          console.log("finished running web performance on link",i)
          measureWebsitePerformance(i+1)
        }
      });
    })

  }else{
    console.log("Done collecting pageLoad Results from all sites")
    process.exit();
  }

}

// var topSites=JSON.parse(fs.readFileSync('USalexatop50.json'),'utf8')
var topSites=[]
const data=fs.readFileSync('USalexatop50.txt','UTF-8')
const lines=data.split(/\r?\n/);
lines.forEach((line)=>{
  if (line!='') topSites.push(line);
});
measureWebsitePerformance(0)