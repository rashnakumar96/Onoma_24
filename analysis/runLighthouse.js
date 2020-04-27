//To install lighthouse run the following commands:
// 1. brew install yarn
// 2. yarn global add lighthouse 


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
  // uncomment the next line if want to run tests in headless mode
  // chromeFlags: ['--headless'],
  onlyCategories: ['performance']
};


function measureWebsitePerformance(i,dir){
  if (i<topSites.length){
    var url="http://"+topSites[i]
    console.log(url)
    launchChromeAndRunLighthouse(url,opts).then(results => {
      if (!fs.existsSync(dir)){
        fs.mkdirSync(dir)
      }
      fs.writeFile(dir+topSites[i]+'Lighthouse.json',results,(err)=>{
        if (err){
          console.log('Error in writting Data to file',err);
        }
        else{
          console.log("finished running web performance on link",i)
          measureWebsitePerformance(i+1,dir)
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


//Execute the three calls by setting the DNS resolver accordingly
// measureWebsitePerformance(0,"lighthouseResultsLocalR/")
// measureWebsitePerformance(0,"lighthouseResultsSubRosa/")
// measureWebsitePerformance(0,"lighthouseResultsDoHProxy/")
measureWebsitePerformance(0,"lighthouseResultsGoogleDoH/")




