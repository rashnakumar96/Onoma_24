const { ipcRenderer } = require('electron');
const path = require('path');
const childProcess = require('child_process');
var { PythonShell } = require('python-shell');
var sudo = require('sudo-prompt');
var options = {
    name: 'Sub Rosa',
};

var projectSrc = __dirname.split(path.sep).slice(0, -1).join(path.sep);
console.log(projectSrc);

document.getElementById("start").addEventListener("click", function(){
    sudo.exec(path.join(projectSrc, "bin", getOS(), "namehelp --service start"), options, function(error, stdout, stderr) {
        if (error) throw error;
        console.log('stdout: ' + stdout);
    });
});

document.getElementById("measurement").addEventListener("click", function(){
    if (getOS() == "Windows") {
        var pyOptions = {
            pythonPath: path.join(projectSrc, "analysis", "envs", "python"),
            args: []
        };
    } else if (getOS() == "MacOS") {
        var pyOptions = {
            pythonPath: path.join(projectSrc, "analysis", "envs", "bin", "python"),
            args: []
        };
    }

    PythonShell.run(path.join(projectSrc, "analysis", "runTests.py"), pyOptions, function (err, results) {
        if (err) throw err;
        // results is an array consisting of messages collected during execution
        console.log('results:', results);
    });
    // const command = `conda run -n subrosa_env python runTests.py`
    
    // const pythonProcess = childProcess.spwan(command, { shell: true });
    
    // pythonProcess.stdin.on('data', (data) => console.log(data.toString()));
    // pythonProcess.stderr.on('data', (data) => console.error(data.toString()));
    
    // pythonProcess.on('close', (code) => {
    //     console.log('Process Exited:', code);
    // });
});

document.getElementById("stop").addEventListener("click", function(){
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