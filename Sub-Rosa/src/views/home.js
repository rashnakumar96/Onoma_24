const { ipcRenderer } = require('electron');
const path = require('path');
var exec = require('child_process').exec, child;
var { PythonShell } = require('python-shell');
var sudo = require('sudo-prompt');
var options = {
    name: 'Sub-Rosa',
};

var projectSrc = __dirname.split(path.sep).slice(0, -1).join(path.sep);
console.log(projectSrc);

document.getElementById("install").addEventListener("click", function(){
    var commandPath = path.join(projectSrc, "analysis", "runTests_mac.command");
    var osaCommand = "osascript -e 'tell application \"System Events\" to make login item at end with properties {path:\""
                   + commandPath
                   + "\", hidden:false}'";
    child = exec(osaCommand,
    function (error, stdout, stderr) {
        console.log('stdout: ' + stdout);
        console.log('stderr: ' + stderr);
        if (error !== null) {
             console.log('exec error: ' + error);
        }
    });
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service install"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("start").addEventListener("click", function(){
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service start"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("measurement").addEventListener("click", function(){
    // if (getOS() == "Windows") {
    //     var pyOptions = {
    //         pythonPath: path.join(projectSrc, "analysis", "envs", "python"),
    //         args: []
    //     };
    // } else if (getOS() == "MacOS") {
    //     var pyOptions = {
    //         pythonPath: path.join(projectSrc, "analysis", "envs", "bin", "python"),
    //         args: []
    //     };
    // }

    // PythonShell.run(path.join(projectSrc, "analysis", "runTests.py"), pyOptions, function (err, results) {
    //     if (err) throw err;
    //     // results is an array consisting of messages collected during execution
    //     console.log('results:', results);
    // });
    
    var command = path.join(projectSrc, "analysis", "runTests_mac.command")
    child = exec(command,
    function (error, stdout, stderr) {
        console.log('stdout: ' + stdout);
        console.log('stderr: ' + stderr);
        if (error !== null) {
             console.log('exec error: ' + error);
        }
    });
});

document.getElementById("stop").addEventListener("click", function(){
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service stop"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("uninstall").addEventListener("click", function(){
    var osaCommand = "osascript -e 'tell application \"System Events\" to delete login item \"runTests_mac.command\"'";
    child = exec(osaCommand,
    function (error, stdout, stderr) {
        console.log('stdout: ' + stdout);
        console.log('stderr: ' + stderr);
        if (error !== null) {
             console.log('exec error: ' + error);
        }
    });
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