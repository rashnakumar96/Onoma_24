const { ipcRenderer } = require('electron');
const path = require('path');

var sudo = require('sudo-prompt');
var options = {
  name: 'Sub Rosa',
};

var projectSrc = __dirname.split('/').slice(0, -1).join('/');
console.log(projectSrc);

document.getElementById("start").addEventListener("click", function(){
    alert("Starting Sub-Rosa Service");
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service start"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("stop").addEventListener("click", function(){
    alert("Stopping Sub-Rosa Service");
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service stop"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("install").addEventListener("click", function(){
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service install"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("uninstall").addEventListener("click", function(){
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service uninstall"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

function getOS() {
    var userAgent = window.navigator.userAgent,
        platform = window.navigator.platform,
        macosPlatforms = ['Macintosh', 'MacIntel', 'MacPPC', 'Mac68K'],
        windowsPlatforms = ['Win32', 'Win64', 'Windows', 'WinCE'],
        iosPlatforms = ['iPhone', 'iPad', 'iPod'],
        os = null;
  
    if (macosPlatforms.indexOf(platform) !== -1) {
      os = 'MacOS';
    } else if (iosPlatforms.indexOf(platform) !== -1) {
      os = 'iOS';
    } else if (windowsPlatforms.indexOf(platform) !== -1) {
      os = 'Windows';
    } else if (/Android/.test(userAgent)) {
      os = 'Android';
    } else if (!os && /Linux/.test(platform)) {
      os = 'Linux';
    } 
  
    return os;
  }