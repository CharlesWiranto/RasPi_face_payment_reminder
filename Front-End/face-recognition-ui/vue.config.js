const { defineConfig } = require('@vue/cli-service')
// module.exports = defineConfig({
//   transpileDependencies: true
// })
module.exports = {
  devServer: {
    port: 8086, // change if needed
    proxy: {
      '/api': {
        target: 'http://192.168.98.119:5000', // backend address / RASPBERRY PI
        changeOrigin: true,
        pathRewrite: {
          // '^/api': ''
        }
      },
      '/video_feed': {
        target: 'http://192.168.98.119:5000',
        changeOrigin: true
      }
    },
    hot: true,
    liveReload: true,
    allowedHosts : ['all'],
    // Disable WebSocket proxy to prevent /ws requests to backend
    webSocketServer: false


    // watchOptions: {
    //   poll: 1000,
    // }
  }
}