//To install lighthouse run the following commands:
// 1. brew install yarn
// 2. yarn global add lighthouse 


'use strict';
const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');
const fs=require('fs');
var ReadWriteLock = require('rwlock');
var lock = new ReadWriteLock();


function launchChromeAndRunLighthouse(url, opts,config = null) {
  // return chromeLauncher.launch({chromeFlags: opts.chromeFlags}).then(chrome => {
    // opts.port = chrome.port;
    
    return lighthouse(url, opts, config).then(results => {

        // return chrome.kill().then(() => results.report)
        return results.report
    }).catch((err)=>{console.log("Lighthouse threw an error with the url", url, err);});
    
  // });
}

const opts = {
  chromeFlags: ['--headless'],
  onlyCategories: ['performance'],
};


function measureResourcePerformance(i,dir,dict,topSites,dirPath,chrome,fileNumber){
  if (i<topSites.length){
    var url=topSites[i]
    // console.log(url)
    launchChromeAndRunLighthouse(url,opts).then(results => {
      const obj=JSON.parse(results)
      dict.push({
        website:url,
        // ttfb:obj["audits"]["server-response-time"]["numericValue"]
        ttfb:obj["audits"]["time-to-first-byte"]["numericValue"]
      });      
      console.log("finished running web performance on link", i)  
      measureResourcePerformance(i+1,dir,dict,topSites,dirPath,chrome,fileNumber);
    }).catch((err)=>{
      console.log("Lighthouse threw an error with the url", url, err);
      measureResourcePerformance(i+1,dir,dict,topSites,dirPath,chrome,fileNumber);

    });
  }else{
    console.log("Done collecting pageLoad Results from all sites")
    chrome.kill().then(()=>{
      lock.writeLock(function (release) {
        console.log("writing to file",dirPath+'lighthouseTTB'+dir+fileNumber+".json")
        fs.appendFile(dirPath+'lighthouseTTB'+dir+fileNumber+".json",JSON.stringify(dict,null,4),(err)=>{
        if(err) 
          console.log("write error: ",err);
        else    
          console.log("write ok");
        });
        release(); // unlock
      });
    });
  }
}

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
          console.log('Error in writting Data to file', err);
        }
        else{
          console.log("finished running web performance on link", i)
          measureWebsitePerformance(i+1,dir)
        }
      });
    })

  }else{
    console.log("Done collecting pageLoad Results from all sites")
    process.exit();
  }

}




//measure page load times for resources of USALexa top sites
////////////////////////////////////////////////////////////////////////////////

function startLighthouse(approach,dirPath,resources,fileNumber){
  
    var dict = [];
    // resources=resources.slice(0,3)
    // console.log(resources)
    chromeLauncher.launch({chromeFlags: opts.chromeFlags}).then(chrome => {
      opts.port = chrome.port;
      measureResourcePerformance(0,approach,dict,resources,dirPath,chrome,fileNumber)
    }).catch((err)=>{
      console.log("Lighthouse threw an error with chromeLauncher");
    });

}

var approach=process.argv.slice(0)[3]
var dirPath=process.argv.slice(0)[2]
var fileNumber=process.argv.slice(0)[4]
var resources=process.argv.slice(5)
console.log(resources.length)
console.log(dirPath)
console.log(approach)
console.log("fileNumber: ",fileNumber)

startLighthouse(approach,dirPath,resources,fileNumber)










