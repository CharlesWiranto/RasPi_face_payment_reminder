<template>
  <div class="min-h-screen bg-gray-100 p-8">
    <div class="max-w-4xl mx-auto bg-white rounded-lg shadow-md p-6">
      <h1 class="text-3xl font-bold text-center mb-6">User Registration</h1>
      
      <!-- Camera Section -->
      <!-- <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Capture Face Image</h2>
        <div class="bg-gray-200 rounded-lg overflow-hidden aspect-video mb-4">
          <img 
            v-if="isCameraOn"
            :src="`${config.RASP_URL}/video_feed`" 
            alt="Camera Feed"
            class="w-full h-full object-cover"
          >
          <div v-else class="w-full h-full flex items-center justify-center text-gray-500">
            Camera is off
          </div>
        </div>
        
        <div class="flex flex-wrap gap-2 mb-6">
          <button 
            @click="startCamera"
            :disabled="isCameraOn"
            :class="['px-4 py-2 rounded', 
                    !isCameraOn ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed']"
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
        
        <div v-if="capturedImage" class="mb-6">
          <h3 class="text-lg font-medium mb-2">Captured Face</h3>
          <div class="bg-gray-200 rounded-lg overflow-hidden aspect-video">
            <img :src="capturedImage" alt="Captured Face" class="w-full h-full object-cover">
          </div>
        </div>
      </div> -->

        
      <div class="mb-8">
        <h2 class="text-xl font-semibold mb-4">Capture Face Images (5 required)</h2>
        <div class="bg-gray-200 rounded-lg overflow-hidden aspect-video mb-4">
          <img 
            v-if="isCameraOn"
            :src="`${config.RASP_URL}/video_feed`" 
            alt="Camera Feed"
            class="w-full h-full object-cover"
          >
          <div v-else class="w-full h-full flex items-center justify-center text-gray-500">
            Camera is off
          </div>
        </div>
        
        <div class="flex flex-wrap gap-2 mb-6">
          <button @click="startCamera" :disabled="isCameraOn">
            Start Camera
          </button>
          <button @click="stopCamera" :disabled="!isCameraOn">
            Stop Camera
          </button>
          <button 
            @click="captureImages" 
            :disabled="!isCameraOn || isCapturing"
          >
            {{ isCapturing ? 'Capturing...' : 'Capture 5 Images' }}
          </button>
        </div>
        
        <!-- Captured Images Preview -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
          <div 
            v-for="(image, index) in capturedImages" 
            :key="index"
            class="relative bg-gray-200 rounded overflow-hidden aspect-square"
          >
            <img :src="image.dataUrl" class="w-full h-full object-cover">
            <button 
              @click="removeImage(index)"
              class="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center"
            >
              ×
            </button>
          </div>
        </div>
        
        <!-- <div v-if="capturedImages.length > 0" class="mb-6">
          <h3 class="text-lg font-medium mb-2">Captured Images ({{ capturedImages.length }}/5)</h3>
          <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
            <div 
              v-for="(image, index) in capturedImages" 
              :key="index"
              class="relative bg-gray-200 rounded overflow-hidden aspect-square"
            >
              <img :src="image.url" class="w-full h-full object-cover">
              <button 
                @click="removeImage(index)"
                class="absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center"
              >
                ×
              </button>
            </div>
          </div>
        </div> -->
      </div>
      
      <!-- Registration Form -->
      <div class="space-y-4">
        <div>
          <label for="name" class="block text-sm font-medium text-gray-700">Full Name</label>
          <input 
            v-model="user.name"
            type="text" 
            id="name" 
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            required
          >
        </div>
        
        <div>
          <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
          <input 
            v-model="user.email"
            type="email" 
            id="email" 
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            required
          >
        </div>
        
        <div>
          <label for="alipayId" class="block text-sm font-medium text-gray-700">Alipay User ID (Optional)</label>
          <input 
            v-model="user.alipayId"
            type="text" 
            id="alipayId" 
            class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
          >
        </div>
        
        <button 
          @click="registerUser"
          :disabled="!canSubmit"
          :class="['w-full mt-6 px-4 py-3 rounded-lg font-medium flex items-center justify-center', 
                  canSubmit ? 'bg-indigo-600 text-white hover:bg-indigo-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed']"
        >
          <svg v-if="isRegistering" class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ isRegistering ? 'Registering...' : 'Register User' }}
        </button>
        
        <!-- Success Message -->
        <div v-if="registrationSuccess" class="mt-4 p-4 bg-green-50 text-green-800 rounded-lg">
          <p>Registration successful! User ID: {{ registeredUserId }}</p>
          <router-link 
            to="/recognize" 
            class="mt-2 inline-block text-green-600 hover:text-green-800 font-medium"
          >
            Go to Recognition Page
          </router-link>
          <router-link 
              to="/" 
              class="mt-4 inline-block px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
              Back to Recognition
          </router-link>
        </div>
        
        <!-- Error Message -->
        <div v-if="registrationError" class="mt-4 p-4 bg-red-50 text-red-800 rounded-lg">
          {{ registrationError }}
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
    /*
    async captureImage() {
      try {
        // 调用树莓派的capture接口
        const response = await axios.get(`${config.RASP_URL}/capture`)
        if (response.data.status === 'success') {
          this.capturedImage = response.data.image_url
        } else {
          this.registrationError = 'Capture failed'
        }
      } catch (error) {
        console.error('Error capturing image:', error)
        this.registrationError = 'Error capturing image. Please try again.'
      }
    },
    async registerUser() {
      if (!this.canSubmit) return;
      
      this.isRegistering = true;
      this.registrationError = null;
      
      try {
        const response = await axios.post(`${config.RASP_URL}/api/register`, {
          image_url: this.capturedImage,
          name: this.user.name,
          email: this.user.email,
          alipay_user_id: this.user.alipayId
        });
        
        this.registeredUserId = response.data.user_id;
        this.registrationSuccess = true;
        
        // Reset form after successful registration
        this.user = { name: '', email: '', alipayId: '' };
        this.capturedImage = null;
        this.stopCamera();
      } catch (error) {
        console.error('Registration error:', error);
        this.registrationError = error.response?.data?.error || 'Registration failed. Please try again.';
      } finally {
        this.isRegistering = false;
      }
    }
    
    async captureImages() {
      this.isCapturing = true
      this.registrationError = null
      
      try {
        const response = await axios.post(`${config.RASP_URL}/api/capture_multiple`, {
          count: 5
        })
        console.log(response);
        if (response.data.status === 'success') {
          // Store images in local storage
          const newImages = response.data.images.map(img => ({
            url: img.url,
            filename: img.filename
          }))
          
          this.capturedImages = [...this.capturedImages, ...newImages].slice(0, 10) // Max 10 images
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
    */
    async captureImages() {
      this.isCapturing = true
      this.registrationError = null
      
      try {
        const response = await axios.post(`${config.RASP_URL}/api/capture_multiple`, {
          count: 5
        })
        
        if (response.data.status === 'success') {
          // Create data URLs from base64 images
          const newImages = response.data.images.map(img => ({
            url: img.url,
            filename: img.filename,
            dataUrl: `data:image/jpeg;base64,${img.image}`  // Create data URL
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
      // Convert data URLs to base64 strings for storage
      const imagesToSave = this.capturedImages.map(img => ({
        url: img.url,
        filename: img.filename,
        base64: img.dataUrl.replace('data:image/jpeg;base64,', '')  // Extract base64
      }))
      localStorage.setItem('capturedImages', JSON.stringify(imagesToSave))
    },
    
    loadFromLocalStorage() {
      const saved = localStorage.getItem('capturedImages')
      if (saved) {
        try {
          const savedImages = JSON.parse(saved)
          // Recreate data URLs from base64
          this.capturedImages = savedImages.map(img => ({
            url: img.url,
            filename: img.filename,
            dataUrl: `data:image/jpeg;base64,${img.base64}`  // Recreate data URL
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
    /*
    saveToLocalStorage() {
      localStorage.setItem('capturedImages', JSON.stringify(this.capturedImages))
    },
    
    loadFromLocalStorage() {
      const saved = localStorage.getItem('capturedImages')
      if (saved) {
        this.capturedImages = JSON.parse(saved)
      }
    },
    */
    async registerUser() {
      if (!this.canSubmit) return
      
      this.isRegistering = true
      this.registrationError = null
      
      try {
        // Use the first 5 images
        const imagesToSubmit = this.capturedImages.slice(0, 5).map(img => img.url)
        
        const response = await axios.post(`${config.RASP_URL}/api/register`, {
          images: imagesToSubmit,
          name: this.user.name,
          email: this.user.email,
          alipay_user_id: this.user.alipayId
        })
        console.log(response);
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