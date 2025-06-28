<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <div class="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6">
      <h1 class="text-3xl font-bold text-center mb-6">Face Recognition System</h1>
      
      <!-- Camera Section -->
      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Camera</h2>
        <div class="bg-gray-200 rounded-lg overflow-hidden aspect-video mb-4">
          <video 
            ref="videoElement" 
            v-show="isCameraOn"
            autoplay 
            playsinline 
            class="w-full h-full object-cover"
          ></video>
          <div v-show="!isCameraOn" class="w-full h-full flex items-center justify-center text-gray-500">
            Camera is off
          </div>
        </div>

        <router-link 
          to="/register" 
          class="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Register New User
        </router-link>

        <div class="flex flex-wrap gap-2">
          <button 
            @click="startCamera"
            class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
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
            @click="captureImage"
            :disabled="!isCameraOn"
            :class="['px-4 py-2 rounded', isCameraOn ? 'bg-green-600 text-white hover:bg-green-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed']"
          >
            Capture Image
          </button>
        </div>
      </div>
      
      <!-- Captured Image -->
      <div class="mb-8" v-if="capturedImage">
        <h2 class="text-xl font-semibold mb-4">Captured Image</h2>
        <div class="bg-gray-200 rounded-lg overflow-hidden aspect-video mb-4">
          <img :src="capturedImage" alt="Captured" class="w-full h-full object-cover">
        </div>
      </div>
      
      <!-- Recognition Results -->
      <div v-if="recognitionResult">
        <h2 class="text-xl font-semibold mb-4">Recognition Result</h2>
        <div class="bg-gray-50 p-4 rounded-lg">
          <p><span class="font-medium">Name:</span> {{ recognitionResult.name }}</p>
          <p><span class="font-medium">Confidence:</span> {{ recognitionResult.confidence.toFixed(2) }}%</p>
          <p><span class="font-medium">Time:</span> {{ formatTime(recognitionResult.timestamp) }}</p>
          <div v-if="recognitionResult.emailSent" class="mt-2 text-green-600">
            Email notification sent successfully!
          </div>
        </div>
      </div>
      
      <!-- Recognition Button -->
      <button 
        @click="recognize"
        :disabled="!capturedImage || isRecognizing"
        :class="['w-full mt-6 px-4 py-3 rounded-lg font-medium flex items-center justify-center', 
                (!capturedImage || isRecognizing) ? 'bg-gray-300 text-gray-500 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700']"
      >
        <svg v-if="isRecognizing" class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        {{ isRecognizing ? 'Recognizing...' : 'Recognize Face' }}
      </button>
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
      capturedImage: null,
      recognitionResult: null,
      isRecognizing: false,
      videoStream: null
    }
  },
  methods: {
    async startCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true })
        this.$refs.videoElement.srcObject = stream
        this.videoStream = stream
        this.isCameraOn = true
      } catch (error) {
        console.error('Error accessing camera:', error)
        alert('Could not access the camera. Please ensure you have granted permissions.')
      }
    },
    stopCamera() {
      if (this.videoStream) {
        this.videoStream.getTracks().forEach(track => track.stop())
        this.videoStream = null
        this.isCameraOn = false
      }
    },
    captureImage() {
      const video = this.$refs.videoElement
      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      const ctx = canvas.getContext('2d')
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      
      this.capturedImage = canvas.toDataURL('image/jpeg')
    },
    formatTime(timestamp) {
      return new Date(timestamp).toLocaleString()
    },
    async recognize() {
      if (!this.capturedImage) return
      
      this.isRecognizing = true
      try {
        // Extract base64 data (remove the data:image/jpeg;base64, part)
        const base64Data = this.capturedImage.split(',')[1]
        
        const response = await axios.post(`${config.RASP_URL}/api/recognize`, {
          image: base64Data
        })
        
        this.recognitionResult = response.data
      } catch (error) {
        console.error('Recognition error:', error)
        alert('Face recognition failed. Please try again.')
      } finally {
        this.isRecognizing = false
      }
    }
  },
  beforeUnmount() {
    this.stopCamera()
  }
}
</script>