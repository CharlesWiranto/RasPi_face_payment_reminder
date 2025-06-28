<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <div class="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6">
      <h1 class="text-3xl font-bold text-center mb-6">Face Recognition System</h1>
      
      <!-- Camera Section -->
      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Camera Feed</h2>
        <div class="bg-gray-200 rounded-lg overflow-hidden aspect-video mb-4 relative">
          <img 
            v-if="isCameraOn"
            :src="`${config.RASP_URL}/video_feed`" 
            alt="Camera Feed"
            class="w-full h-full object-cover"
            ref="cameraFeed"
          >
          <div v-else class="w-full h-full flex items-center justify-center text-gray-500">
            Camera is off
          </div>
          
          <!-- Recognition status overlay -->
          <div v-if="recognitionStatus" class="absolute bottom-4 left-4 bg-black bg-opacity-50 text-white px-3 py-2 rounded">
            {{ recognitionStatus }}
          </div>
        </div>

        <div class="flex flex-wrap gap-2">
          <button 
            @click="startCamera"
            :disabled="isCameraOn"
            :class="['px-4 py-2 rounded', !isCameraOn ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed']"
          >
            Start Camera
          </button>
          <button 
            @click="stopCamera"
            :disabled="!isCameraOn"
            :class="['px-4 py-2 rounded', isCameraOn ? 'bg-red-600 text-white hover:bg-red-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed']"
          >
            Stop Camera
          </button>
          <button 
            @click="toggleRecognition"
            :class="['px-4 py-2 rounded', autoRecognize ? 'bg-green-600 text-white' : 'bg-gray-600 text-white']"
          >
            {{ autoRecognize ? 'Auto Recognition ON' : 'Auto Recognition OFF' }}
          </button>
        </div>
      </div>
      
      <!-- Recognition Results -->
      <div v-if="recognitionResults.length > 0" class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Recognition Results</h2>
        <div v-for="(result, index) in recognitionResults" :key="index" class="bg-gray-50 p-4 rounded-lg mb-4">
          <p><span class="font-medium">Name:</span> {{ result.user.name }}</p>
          <p><span class="font-medium">Confidence:</span> {{ result.confidence.toFixed(2) }}%</p>
          <p><span class="font-medium">Time:</span> {{ formatTime(result.timestamp) }}</p>
          <div v-if="result.payment_url" class="mt-2">
            <a :href="result.payment_url" target="_blank" class="text-blue-600 hover:underline">
              Complete Payment
            </a>
          </div>
          <div v-if="result.email_sent" class="mt-2 text-green-600">
            Email notification sent!
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import config from '@/config'

export default {
  name: 'FaceRecognition',
  data() {
    return {
      isCameraOn: false,
      autoRecognize: false,
      recognitionStatus: '',
      recognitionResults: [],
      checkInterval: null,
      config
    }
  },
  methods: {
    startCamera() {
      this.isCameraOn = true
      this.recognitionStatus = 'Camera started'
      
      // Start checking for recognized faces if auto mode is on
      if (this.autoRecognize) {
        this.startRecognitionCheck()
      }
    },
    stopCamera() {
      this.isCameraOn = false
      this.recognitionStatus = 'Camera stopped'
      this.stopRecognitionCheck()
    },
    toggleRecognition() {
      this.autoRecognize = !this.autoRecognize
      
      if (this.autoRecognize && this.isCameraOn) {
        //this.startRecognitionCheck()
        this.handleNewRecognitions();
      } else {
        this.stopRecognitionCheck()
      }
    },
    /*
    startRecognitionCheck() {
      // Check every 5 seconds for recognized faces
      this.checkInterval = setInterval(async () => {
        if (!this.isCameraOn) return
        
        try {
          this.recognitionStatus = 'Checking for faces...'
          
          // Capture current frame
          const captureResponse = await axios.get(`${config.RASP_URL}/capture`)
          if (captureResponse.data.status !== 'success') {
            this.recognitionStatus = 'Capture failed'
            return
          }
          console.log(captureResponse.data)
          // Recognize faces
          const recognizeResponse = await axios.post(`${config.RASP_URL}/api/recognize`, {
            image_url: captureResponse.data.image_url
          })
          console.log(recognizeResponse)
          if (recognizeResponse.data.status === 'success') {
            this.recognitionResults = recognizeResponse.data.results
            if (this.recognitionResults.length > 0) {
              this.recognitionStatus = `Recognized ${this.recognitionResults.length} face(s)`
            } else {
              this.recognitionStatus = 'No recognized faces'
            }
          } else {
            this.recognitionStatus = 'Recognition failed'
          }
        } catch (error) {
          console.error('Recognition check error:', error)
          this.recognitionStatus = 'Error during recognition'
        }
      }, 5000) // Check every 5 seconds
    },*/
    async startRecognitionCheck() {
      // Check every 5 seconds for recognized faces
      this.checkInterval = setInterval(async () => {
        if (!this.isCameraOn) return
        
        try {
          this.recognitionStatus = 'Checking for faces...'
          
          // Capture current frame
          const captureResponse = await axios.get(`${config.RASP_URL}/capture`)
          if (captureResponse.data.status !== 'success') {
            this.recognitionStatus = 'Capture failed'
            return
          }

          // Recognize faces
          const recognizeResponse = await axios.post(`${config.RASP_URL}/api/recognize`, {
            image_url: captureResponse.data.image_url
          })

          if (recognizeResponse.data.status === 'success') {
            this.recognitionResults = recognizeResponse.data.results
            
            if (this.recognitionResults.length > 0) {
              this.recognitionStatus = `Recognized ${this.recognitionResults.length} face(s)`
              
              // Check if we need to send emails for newly recognized users
              this.handleNewRecognitions(this.recognitionResults)
            } else {
              this.recognitionStatus = 'No recognized faces'
            }
          } else {
            this.recognitionStatus = 'Recognition failed'
          }
        } catch (error) {
          console.error('Recognition check error:', error)
          this.recognitionStatus = 'Error during recognition'
        }
      }, 5000) // Check every 5 seconds
    },

    async handleNewRecognitions() {
      try {
        this.recognitionStatus = 'Checking for recognized faces...';
        
        // First get the recognition results
        const recognitionResponse = await axios.get(`${config.RASP_URL}/api/get_recognition_results`);
        
        if (recognitionResponse.data.success && recognitionResponse.data.results.length > 0) {
          this.recognitionResults = recognitionResponse.data.results;
          this.recognitionStatus = `Found ${recognitionResponse.data.results.length} recognized face(s)`;
          const data = this.recognitionResults
          // Then send emails for these recognitions
          const emailResponse = await axios.post(`${config.RASP_URL}/api/send_recognition_email`, {data});
          
          if (emailResponse.data.success) {
            // Update which results had emails sent
            console.log(emailResponse);
            this.recognitionResults.forEach(result => {
              const emailResult = emailResponse.data.results.find(
                r => r.user.id === result.user.id
              );
              if (emailResult) {
                result.email_sent = emailResult.email_sent;
                result.payment_url = emailResult.payment_url;
                
                if (emailResult.email_sent) {
                  console.log(`Email sent to ${result.user.name}`);
                  /*
                  this.$notify({
                    title: 'Email Sent',
                    message: `Notification sent to ${result.user.name}`,
                    type: 'success'
                  });
                  */
                }
              }
            });
          }
        } else {
          this.recognitionStatus = recognitionResponse.data.error || 'No faces recognized';
        }
      } catch (error) {
        console.error('Recognition check error:', error);
        this.recognitionStatus = 'Error during recognition';
        console.log("Failed recognizing");
        /*
        this.$notify({
          title: 'Error',
          message: 'Failed to recognize faces',
          type: 'error'
        });
        */
      }
    },
    stopRecognitionCheck() {
      if (this.checkInterval) {
        clearInterval(this.checkInterval)
        this.checkInterval = null
      }
    },


    formatTime(timestamp) {
      return new Date(timestamp).toLocaleString()
    }
  },
  unmounted() {
    this.stopRecognitionCheck()
  }
}
</script>