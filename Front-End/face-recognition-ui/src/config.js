const config = {
    // Development configuration
    development: {
      // RASP_URL: 'http://charles.free.idcfengye.com' // Your Raspberry Pi local IP
      RASP_URL: 'http://192.168.98.119:5000'
    },
    // Production configuration
    production: {
      // RASP_URL: 'http://charles.free.idcfengye.com'
      RASP_URL: 'http://192.168.98.119:5000'
    }
  }
  
/*
前端
sunny-server=free idcfengye.com:4443_key=171035448313
http://our.free.idcfengye.com/

后端
sunny-server=free.idcfengye.com 4443-key-180753448317
http://charles.free.idcfengye.com/
*/

  // Export the appropriate config based on environment
  export default config[process.env.NODE_ENV] || config.development