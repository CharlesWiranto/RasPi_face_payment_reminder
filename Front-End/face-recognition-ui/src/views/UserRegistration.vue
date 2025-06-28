<template>
  <div class="min-h-screen bg-cover bg-gray-100 bg-opacity-90 bg-center bg-no-repeat p-4 md:p-8">
  <!-- <div class="min-h-screen bg-cover bg-center bg-no-repeat p-4 md:p-8" :style="{backgroundImage: `url(${require('@/assets/UserRegistration_BG.png')})`}"> -->
    <div class="max-w-6xl mx-auto bg-white bg-opacity-90 rounded-xl shadow-lg overflow-hidden backdrop-blur-sm">      <!-- Header with navigation -->
      <div class="bg-indigo-700 px-6 py-4 flex justify-between items-center">
        <h1 class="text-2xl md:text-3xl font-bold text-white">User Registration</h1>
        <router-link 
          to="/" 
          class="px-4 py-2 bg-white text-indigo-700 rounded-lg font-medium hover:bg-indigo-100 transition-colors"
        >
          Back to Recognition
        </router-link>
      </div>
      
      <div class="p-6">
        <!-- Camera Section -->
        <div class="mb-8">
          <h2 class="text-xl font-semibold mb-4 text-gray-800">Capture Face Images (5 required)</h2>
          <div class="bg-gray-200 rounded-xl overflow-hidden aspect-video mb-4 relative border-4 border-gray-300">
            <img 
              v-if="isCameraOn"
              :src="`${config.RASP_URL}/video_feed`" 
              alt="Camera Feed"
              class="w-full h-full object-cover"
            >
            <div v-else class="w-full h-full flex items-center justify-center text-gray-500 bg-gray-100">
              <div class="text-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p class="mt-2">Camera is currently off</p>
              </div>
            </div>
            
            <!-- Capture progress indicator -->
            <div v-if="isCapturing" class="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center">
              <div class="text-center text-white">
                <svg class="animate-spin h-10 w-10 mx-auto text-white mb-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p class="font-medium">Capturing images...</p>
              </div>
            </div>
          </div>
          
          <div class="flex flex-wrap gap-3 mb-6">
            <button 
              @click="startCamera" 
              :disabled="isCameraOn"
              class="px-5 py-2.5 rounded-lg font-medium flex items-center transition-colors"
              :class="!isCameraOn ? 
                'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md' : 
                'bg-gray-200 text-gray-500 cursor-not-allowed'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
              Start Camera
            </button>
            <button 
              @click="stopCamera" 
              :disabled="!isCameraOn"
              class="px-5 py-2.5 rounded-lg font-medium flex items-center transition-colors"
              :class="isCameraOn ? 
                'bg-red-600 text-white hover:bg-red-700 shadow-md' : 
                'bg-gray-200 text-gray-500 cursor-not-allowed'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clip-rule="evenodd" />
              </svg>
              Stop Camera
            </button>
            <button 
              @click="captureImages" 
              :disabled="!isCameraOn || isCapturing"
              class="px-5 py-2.5 rounded-lg font-medium flex items-center transition-colors shadow-md"
              :class="!isCameraOn || isCapturing ? 
                'bg-gray-200 text-gray-500 cursor-not-allowed' : 
                'bg-green-600 text-white hover:bg-green-700'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 5a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V7a2 2 0 00-2-2h-1.586a1 1 0 01-.707-.293l-1.121-1.121A2 2 0 0011.172 3H8.828a2 2 0 00-1.414.586L6.293 4.707A1 1 0 015.586 5H4zm6 9a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
              </svg>
              {{ isCapturing ? 'Capturing...' : 'Capture 5 Images' }}
            </button>
          </div>
          
          <!-- Captured Images Preview -->
          <div>
            <h3 class="text-lg font-medium mb-3 text-gray-800">
              Captured Images 
              <span class="text-sm font-normal text-gray-500">({{ capturedImages.length }}/5 required)</span>
            </h3>
            
            <div v-if="capturedImages.length > 0" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
              <div 
                v-for="(image, index) in capturedImages" 
                :key="index"
                class="relative bg-gray-200 rounded-lg overflow-hidden aspect-square border-2 border-gray-300"
              >
                <img :src="image.dataUrl" class="w-full h-full object-cover">
                <button 
                  @click="removeImage(index)"
                  class="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center hover:bg-red-600 transition-colors"
                >
                  ×
                </button>
                <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 text-center">
                  Image {{ index + 1 }}
                </div>
              </div>
            </div>
            <div v-else class="bg-gray-50 rounded-lg p-4 text-center text-gray-500">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p class="mt-2">No images captured yet</p>
            </div>
          </div>
        </div>
        
        <!-- Registration Form -->
        <div class="space-y-6">
          <h2 class="text-xl font-semibold text-gray-800">User Information</h2>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label for="name" class="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
              <input 
                v-model="user.name"
                type="text" 
                id="name" 
                class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                placeholder="John Doe"
                required
              >
            </div>
            
            <div>
              <label for="email" class="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input 
                v-model="user.email"
                type="email" 
                id="email" 
                class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                placeholder="john@example.com"
                required
              >
            </div>
            
            <div>
              <label for="alipayId" class="block text-sm font-medium text-gray-700 mb-1">Alipay User ID</label>
              <input 
                v-model="user.alipayId"
                type="text" 
                id="alipayId" 
                class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all"
                placeholder="Optional"
              >
            </div>
          </div>
          
          <button 
            @click="registerUser"
            :disabled="!canSubmit"
            class="w-full mt-6 px-6 py-3.5 rounded-lg font-medium flex items-center justify-center transition-colors shadow-md"
            :class="canSubmit ? 
              'bg-indigo-600 text-white hover:bg-indigo-700' : 
              'bg-gray-300 text-gray-500 cursor-not-allowed'"
          >
            <svg v-if="isRegistering" class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ isRegistering ? 'Registering...' : 'Register User' }}
          </button>
          
          <!-- Success Message -->
          <div v-if="registrationSuccess" class="mt-6 p-5 bg-green-50 border border-green-200 rounded-xl">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-green-800">
                  Registration successful!
                </h3>
                <div class="mt-2 text-sm text-green-700">
                  <p>User ID: <span class="font-medium">{{ registeredUserId }}</span></p>
                </div>
                <div class="mt-4">
                  <div class="-mx-2 -my-1.5 flex">
                    <router-link 
                      to="/" 
                      class="px-3 py-1.5 rounded-md text-sm font-medium bg-green-100 text-green-800 hover:bg-green-200"
                    >
                      Go to Recognition Page
                    </router-link>
                    <router-link 
                      to="/" 
                      class="ml-3 px-3 py-1.5 rounded-md text-sm font-medium bg-gray-100 text-gray-800 hover:bg-gray-200"
                    >
                      Back to Home
                    </router-link>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Error Message -->
          <div v-if="registrationError" class="mt-6 p-5 bg-red-50 border border-red-200 rounded-xl">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-red-800">
                  Registration error
                </h3>
                <div class="mt-2 text-sm text-red-700">
                  <p>{{ registrationError }}</p>
                </div>
              </div>
            </div>
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
  name: 'UserRegistration',
  data() {
    return {
      isCameraOn: false,
      capturedImage: null,
      isRegistering: false,
      registrationSuccess: false,
      registrationError: null,
      registeredUserId: null,
      config,
      capturedImages: [],
      isCapturing: false,
      user: {
        name: '',
        email: '',
        alipayId: ''
      }
    }
  },
  computed: {
    canSubmit() {
      return (
        this.capturedImages.length >= 5 && 
        this.user.name && 
        this.user.email && 
        !this.isRegistering
      )
    }
  },
  methods: {
    startCamera() {
      this.isCameraOn = true
    },
    stopCamera() {
      this.isCameraOn = false
    },
    
    async captureImages() {
      this.isCapturing = true
      this.registrationError = null
      
      try {
        const response = await axios.post(`${config.RASP_URL}/api/capture_multiple`, {
          count: 5
        })
        
        if (response.data.status === 'success') {
          const newImages = response.data.images.map(img => ({
            url: img.url,
            filename: img.filename,
            dataUrl: `data:image/jpeg;base64,${img.image}`
          }))
          
          this.capturedImages = [...this.capturedImages, ...newImages].slice(0, 10)
          this.saveToLocalStorage()
        } else {
          this.registrationError = 'Capture failed: ' + (response.data.error || 'Unknown error')
        }
      } catch (error) {
        console.error('Error capturing images:', error)
        this.registrationError = 'Error capturing images. Please try again.'
      } finally {
        this.isCapturing = false
      }
    },
    
    saveToLocalStorage() {
      const imagesToSave = this.capturedImages.map(img => ({
        url: img.url,
        filename: img.filename,
        base64: img.dataUrl.replace('data:image/jpeg;base64,', '')
      }))
      localStorage.setItem('capturedImages', JSON.stringify(imagesToSave))
    },
    
    loadFromLocalStorage() {
      const saved = localStorage.getItem('capturedImages')
      if (saved) {
        try {
          const savedImages = JSON.parse(saved)
          this.capturedImages = savedImages.map(img => ({
            url: img.url,
            filename: img.filename,
            dataUrl: `data:image/jpeg;base64,${img.base64}`
          }))
        } catch (e) {
          console.error('Error loading images from localStorage:', e)
          localStorage.removeItem('capturedImages')
        }
      }
    },
    
    removeImage(index) {
      this.capturedImages.splice(index, 1)
      this.saveToLocalStorage()
    },
    
    async registerUser() {
      if (!this.canSubmit) return
      
      this.isRegistering = true
      this.registrationError = null
      
      try {
        const imagesToSubmit = this.capturedImages.slice(0, 5).map(img => img.url)
        
        const response = await axios.post(`${config.RASP_URL}/api/register`, {
          images: imagesToSubmit,
          name: this.user.name,
          email: this.user.email,
          alipay_user_id: this.user.alipayId
        })
        
        this.registeredUserId = response.data.user_id
        this.registrationSuccess = true
        
        // Clear after successful registration
        this.user = { name: '', email: '', alipayId: '' }
        this.capturedImages = []
        localStorage.removeItem('capturedImages')
        this.stopCamera()
      } catch (error) {
        console.error('Registration error:', error)
        this.registrationError = error.response?.data?.error || 'Registration failed. Please try again.'
      } finally {
        this.isRegistering = false
      }
    },
  },
  mounted() {
    this.loadFromLocalStorage()
  }
}
</script>