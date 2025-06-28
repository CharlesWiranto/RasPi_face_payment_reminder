<template>
  <div class="min-h-screen bg-cover bg-center  bg-gray-100 bg-opacity-90 bg-no-repeat p-4 md:p-8">
  <!-- <div class="min-h-screen bg-cover bg-center bg-no-repeat p-4 md:p-8" :style="{ backgroundImage: `url(${require('@/assets/FaceRecognition_BG.png')})` }"></div> -->
    <div class="max-w-6xl mx-auto bg-white bg-opacity-90 rounded-xl shadow-lg overflow-hidden backdrop-blur-sm">
      <!-- Header with navigation -->
      <div class="bg-indigo-700 px-6 py-4 flex justify-between items-center">
        <h1 class="text-2xl md:text-3xl font-bold text-white">Face Recognition System</h1>
        <router-link 
          to="/register" 
          class="px-4 py-2 bg-white text-indigo-700 rounded-lg font-medium hover:bg-indigo-100 transition-colors"
        >
          Register New User
        </router-link>
      </div>
      
      <div class="p-6">
        <!-- Camera Section -->
        <div class="mb-8">
          <h2 class="text-xl font-semibold mb-4 text-gray-800">Camera Feed</h2>
          <div class="bg-gray-200 rounded-xl overflow-hidden aspect-video mb-4 relative border-4 border-gray-300">
            <img 
              v-if="isCameraOn"
              :src="`${config.RASP_URL}/video_feed`" 
              alt="Camera Feed"
              class="w-full h-full object-cover"
              ref="cameraFeed"
            >
            <div v-else class="w-full h-full flex items-center justify-center text-gray-500 bg-gray-100">
              <div class="text-center">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <p class="mt-2">Camera is currently off</p>
              </div>
            </div>
            
            <!-- Recognition status overlay -->
            <div v-if="recognitionStatus" class="absolute bottom-4 left-4 bg-black bg-opacity-70 text-white px-4 py-2 rounded-lg text-sm font-medium">
              <span class="inline-block w-2 h-2 rounded-full mr-2" :class="{
                'bg-green-400': recognitionStatus.includes('Recognized'),
                'bg-yellow-400': recognitionStatus.includes('Checking'),
                'bg-red-400': recognitionStatus.includes('failed') || recognitionStatus.includes('Error')
              }"></span>
              {{ recognitionStatus }}
            </div>
          </div>

          <div class="flex flex-wrap gap-3">
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
              @click="toggleRecognition"
              class="px-5 py-2.5 rounded-lg font-medium flex items-center transition-colors shadow-md"
              :class="autoRecognize ? 
                'bg-green-600 text-white hover:bg-green-700' : 
                'bg-gray-600 text-white hover:bg-gray-700'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
              </svg>
              {{ autoRecognize ? 'Auto Recognition ON' : 'Auto Recognition OFF' }}
            </button>
          </div>
        </div>
        
        <!-- Recognition Results -->
        <div v-if="recognitionResults.length > 0" class="mb-8">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-semibold text-gray-800">Recognition Results</h2>
            <span class="bg-indigo-100 text-indigo-800 text-sm font-medium px-3 py-1 rounded-full">
              {{ recognitionResults.length }} result(s)
            </span>
          </div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div 
              v-for="(result, index) in recognitionResults" 
              :key="index" 
              class="bg-white border border-gray-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow"
            >
              <div class="flex items-start space-x-4">
                <div class="flex-shrink-0">
                  <div class="h-12 w-12 rounded-full bg-indigo-100 flex items-center justify-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-lg font-medium text-gray-900 truncate">{{ result.user.name }}</p>
                  <div class="mt-2 space-y-1">
                    <div class="flex items-center text-sm text-gray-500">
                      <svg xmlns="http://www.w3.org/2000/svg" class="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                      Confidence: <span class="font-medium ml-1">{{ result.confidence.toFixed(2) }}%</span>
                    </div>
                    <div class="flex items-center text-sm text-gray-500">
                      <svg xmlns="http://www.w3.org/2000/svg" class="flex-shrink-0 mr-1.5 h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {{ formatTime(result.timestamp) }}
                    </div>
                  </div>
                  
                  <div v-if="result.payment_url" class="mt-3">
                    <a 
                      :href="result.payment_url" 
                      target="_blank" 
                      class="inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded-full shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                    >
                      Complete Payment
                    </a>
                  </div>
                  <div v-if="result.email_sent" class="mt-2 flex items-center text-sm text-green-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                    Email notification sent!
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 舵机控制面板 -->
    <div class="servo-control-panel">
      <h3>🎛️ 舵机控制</h3>
      
      <!-- 模式选择下拉框 -->
      <div class="mode-selector">
        <label for="servo-mode">控制模式：</label>
        <select 
          id="servo-mode" 
          v-model="servoMode" 
          @change="onModeChange"
          class="mode-dropdown"
        >
          <option value="manual">手动控制</option>
          <option value="auto">自动循环</option>
          <option value="face-track">人脸跟踪</option>
        </select>
        <span class="mode-status" :class="getModeStatusClass()">
          {{ getModeStatusText() }}
        </span>
      </div>

      <!-- 手动控制模式 -->
      <div v-if="servoMode === 'manual'" class="manual-control">
        <!-- 水平舵机控制 -->
        <div class="angle-control">
          <label for="angle-slider-hori">水平角度控制 (0° - 180°)：</label>
          <div class="slider-container">
            <input
              id="angle-slider-hori"
              type="range"
              min="0"
              max="180"
              step="5"
              v-model="currentAngleHori"
              @input="onAngleChangeHori"
              @change="setServoAngleHori"
              class="angle-slider"
            />
            <div class="angle-display">
              <span class="angle-value">{{ currentAngleHori }}°</span>
              <div class="angle-indicators">
                <span class="indicator left">0°</span>
                <span class="indicator center">90°</span>
                <span class="indicator right">180°</span>
              </div>
            </div>
          </div>
          <div class="quick-angles">
            <button 
              v-for="angle in quickAngles" 
              :key="'hori-' + angle"
              @click="setQuickAngleHori(angle)"
              :class="['quick-btn', { active: currentAngleHori == angle }]"
            >
              {{ angle }}°
            </button>
          </div>
        </div>

        <!-- 垂直舵机控制 -->
        <div class="angle-control">
          <label for="angle-slider-vert">垂直角度控制 (0° - 180°)：</label>
          <div class="slider-container">
            <input
              id="angle-slider-vert"
              type="range"
              min="0"
              max="180"
              step="5"
              v-model="currentAngleVert"
              @input="onAngleChangeVert"
              @change="setServoAngleVert"
              class="angle-slider vertical-slider"
            />
            <div class="angle-display">
              <span class="angle-value">{{ currentAngleVert }}°</span>
              <div class="angle-indicators">
                <span class="indicator left">0°</span>
                <span class="indicator center">90°</span>
                <span class="indicator right">180°</span>
              </div>
            </div>
          </div>
          <div class="quick-angles">
            <button 
              v-for="angle in quickAngles" 
              :key="'vert-' + angle"
              @click="setQuickAngleVert(angle)"
              :class="['quick-btn', { active: currentAngleVert == angle }]"
            >
              {{ angle }}°
            </button>
          </div>
        </div>
      </div>

      <!-- 自动循环模式 -->
      <div v-if="servoMode === 'auto'" class="auto-control">
        <div class="loop-settings">
          <label for="loop-duration">循环周期 (秒)：</label>
          <input
            id="loop-duration"
            type="number"
            min="1"
            max="10"
            step="0.5"
            v-model="loopDuration"
            class="duration-input"
          />
        </div>
        <div class="loop-controls">
          <button 
            @click="toggleAutoLoop"
            :class="['loop-btn', { active: autoLoopActive, stop: autoLoopActive }]"
            :disabled="servoLoading"
          >
            <span class="btn-icon">{{ autoLoopActive ? '⏹️' : '▶️' }}</span>
            {{ autoLoopActive ? '停止循环' : '开始循环' }}
          </button>
          <div v-if="autoLoopActive" class="loop-status">
            <div class="status-indicator"></div>
            <span>循环运行中 ({{ loopDuration }}s周期)</span>
          </div>
        </div>
      </div>

      <!-- 人脸跟踪模式 -->
      <div v-if="servoMode === 'face-track'" class="face-track-control">
        <div class="track-info">
          <p>📱 人脸跟踪模式将自动扫描环境并跟踪检测到的人脸</p>
          <ul>
            <li>🔍 首先进行8秒环境扫描 (0°-180°)</li>
            <li>👤 检测到人脸后自动跟踪并居中</li>
            <li>🎯 识别成功后保持位置3秒</li>
          </ul>
        </div>
        <button 
          @click="toggleFaceTracking"
          :class="['track-btn', { active: faceTrackingActive, stop: faceTrackingActive }]"
          :disabled="servoLoading"
        >
          <span class="btn-icon">{{ faceTrackingActive ? '⏹️' : '🎯' }}</span>
          {{ faceTrackingActive ? '停止跟踪' : '开始人脸跟踪' }}
        </button>
        <div v-if="faceTrackingActive" class="tracking-status">
          <div class="status-indicator scanning"></div>
          <span>{{ faceTrackingStatus }}</span>
        </div>
      </div>

      <!-- 舵机状态显示 -->
      <div class="servo-status">
        <div class="status-item">
          <span class="label">水平角度：</span>
          <span class="value">{{ servoStatus.current_angle_hori || 90 }}°</span>
        </div>
        <div class="status-item">
          <span class="label">垂直角度：</span>
          <span class="value">{{ servoStatus.current_angle_vert || 90 }}°</span>
        </div>
        <div v-if="servoLoading" class="loading-indicator">
          <div class="spinner"></div>
          <span>操作中...</span>
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
      config,
      // 舵机控制相关
      servoMode: 'manual', // 'manual', 'auto', 'face-track'
      currentAngleHori: 90,  // 水平舵机角度
      currentAngleVert: 90,  // 垂直舵机角度
      loopDuration: 2.0,
      autoLoopActive: false,
      faceTrackingActive: false,
      faceTrackingStatus: '准备就绪',
      servoLoading: false,
      servoStatus: {},
      quickAngles: [0, 45, 90, 135, 180],
    }
  },
  methods: {
    startCamera() {
      this.isCameraOn = true
      this.recognitionStatus = 'Camera started'
      
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
        this.handleNewRecognitions();
      } else {
        this.stopRecognitionCheck()
      }
    },

    async handleNewRecognitions() {
      try {
        this.recognitionStatus = 'Checking for recognized faces...';
        
        const recognitionResponse = await axios.get(`${config.RASP_URL}/api/get_recognition_results`);
        
        if (recognitionResponse.data.success && recognitionResponse.data.results.length > 0) {
          this.recognitionResults = recognitionResponse.data.results;
          this.recognitionStatus = `Found ${recognitionResponse.data.results.length} recognized face(s)`;
          
          // Turn off auto recognition after getting results
          this.autoRecognize = false;
          
          const data = this.recognitionResults
          const emailResponse = await axios.post(`${config.RASP_URL}/api/send_recognition_email`, {data});
          
          if (emailResponse.data.success) {
            this.recognitionResults.forEach(result => {
              const emailResult = emailResponse.data.results.find(
                r => r.user.id === result.user.id
              );
              if (emailResult) {
                result.email_sent = emailResult.email_sent;
                result.payment_url = emailResult.payment_url;
              }
            });
          }
        } else {
          this.recognitionStatus = recognitionResponse.data.error || 'No faces recognized';
        }
      } catch (error) {
        console.error('Recognition check error:', error);
        this.recognitionStatus = 'Error during recognition';
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
    },
        // 舵机控制方法
    async onModeChange() {
      console.log(`🎛️ 切换到${this.servoMode}模式`)
      
      // 停止所有当前活动
      await this.stopAllServoActivity()
      
      // 重置状态
      this.resetModeStates()
      
      // 获取最新状态
      await this.getServoStatus()
    },
    
    async stopAllServoActivity() {
      try {
        this.servoLoading = true
        
        // 停止自动循环
        if (this.autoLoopActive) {
          await this.stopAutoLoop()
        }
        
        // 停止人脸跟踪
        if (this.faceTrackingActive) {
          await this.stopFaceTracking()
        }
        
        // 停止舵机
        await fetch('/api/servo/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        
      } catch (error) {
        console.error('停止舵机活动失败:', error)
      } finally {
        this.servoLoading = false
      }
    },
    
    resetModeStates() {
      this.autoLoopActive = false
      this.faceTrackingActive = false
      this.faceTrackingStatus = '准备就绪'
    },
    
    // 手动控制方法
    onAngleChangeHori() {
      // 实时更新水平角度显示，但不立即发送请求
      // 避免频繁请求
    },
    
    onAngleChangeVert() {
      // 实时更新垂直角度显示，但不立即发送请求
      // 避免频繁请求
    },
    
    async setServoAngleHori() {
      if (this.servoMode !== 'manual') return
      
      try {
        this.servoLoading = true
        const response = await fetch('/api/servo/set_angle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            angle: parseInt(this.currentAngleHori),
            duration: 0.5,
            servo_type: 'horizontal'
          })
        })
        
        const result = await response.json()
        if (result.status === 'success') {
          console.log(`✅ 水平舵机设置到 ${this.currentAngleHori}°`)
          await this.getServoStatus()
        } else {
          throw new Error(result.error || '设置水平角度失败')
        }
      } catch (error) {
        console.error('设置水平舵机角度失败:', error)
        // this.$toast.error(`设置角度失败: ${error.message}`)
      } finally {
        this.servoLoading = false
      }
    },
    
    async setServoAngleVert() {
      if (this.servoMode !== 'manual') return
      
      try {
        this.servoLoading = true
        const response = await fetch('/api/servo/set_angle', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            angle: parseInt(this.currentAngleVert),
            duration: 0.5,
            servo_type: 'vertical'
          })
        })
        
        const result = await response.json()
        if (result.status === 'success') {
          console.log(`✅ 垂直舵机设置到 ${this.currentAngleVert}°`)
          await this.getServoStatus()
        } else {
          throw new Error(result.error || '设置垂直角度失败')
        }
      } catch (error) {
        console.error('设置垂直舵机角度失败:', error)
        // this.$toast.error(`设置角度失败: ${error.message}`)
      } finally {
        this.servoLoading = false
      }
    },
    
    async setQuickAngleHori(angle) {
      this.currentAngleHori = angle
      await this.setServoAngleHori()
    },
    
    async setQuickAngleVert(angle) {
      this.currentAngleVert = angle
      await this.setServoAngleVert()
    },
    
    // 自动循环方法
    async toggleAutoLoop() {
      if (this.autoLoopActive) {
        await this.stopAutoLoop()
      } else {
        await this.startAutoLoop()
      }
    },
    
    async startAutoLoop() {
      try {
        this.servoLoading = true
        const response = await fetch('/api/servo/start_loop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            duration: parseFloat(this.loopDuration)
          })
        })
        
        const result = await response.json()
        if (result.status === 'success') {
          this.autoLoopActive = true
          console.log('✅ 自动循环已启动')
          // this.$toast.success(`自动循环启动 (${this.loopDuration}s周期)`)
        } else {
          throw new Error(result.message || '启动循环失败')
        }
      } catch (error) {
        console.error('启动自动循环失败:', error)
        // this.$toast.error(`启动失败: ${error.message}`)
      } finally {
        this.servoLoading = false
      }
    },
    
    async stopAutoLoop() {
      try {
        this.servoLoading = true
        const response = await fetch('/api/servo/stop_loop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        
        const result = await response.json()
        if (result.status === 'success') {
          this.autoLoopActive = false
          console.log('✅ 自动循环已停止')
          // this.$toast.success('自动循环已停止')
        } else {
          throw new Error(result.message || '停止循环失败')
        }
      } catch (error) {
        console.error('停止自动循环失败:', error)
        // this.$toast.error(`停止失败: ${error.message}`)
      } finally {
        this.servoLoading = false
      }
    },
    
    // 人脸跟踪方法
    async toggleFaceTracking() {
      if (this.faceTrackingActive) {
        await this.stopFaceTracking()
      } else {
        await this.startFaceTracking()
      }
    },
    
    async startFaceTracking() {
      try {
        this.servoLoading = true
        this.faceTrackingStatus = '启动中...'
        
        const response = await fetch('/api/servo/autodetectface', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'start' })
        })
        
        const result = await response.json()
        if (result.status === 'success') {
          this.faceTrackingActive = true
          this.faceTrackingStatus = '环境扫描中 (8秒)...'
          console.log('✅ 人脸跟踪已启动')
          // this.$toast.success('人脸跟踪启动，开始环境扫描')\
          
          // 启动状态监控
          this.startTrackingStatusMonitor()
        } else {
          throw new Error(result.message || '启动人脸跟踪失败')
        }
      } catch (error) {
        console.error('启动人脸跟踪失败:', error)
        // this.$toast.error(`启动失败: ${error.message}`)
        this.faceTrackingStatus = '准备就绪'
      } finally {
        this.servoLoading = false
      }
    },
    
    async stopFaceTracking() {
      try {
        this.servoLoading = true
        this.faceTrackingStatus = '停止中...'
        
        const response = await fetch('/api/servo/autodetectface', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'stop' })
        })
        
        const result = await response.json()
        if (result.status === 'success') {
          this.faceTrackingActive = false
          this.faceTrackingStatus = '准备就绪'
          console.log('✅ 人脸跟踪已停止')
          // this.$toast.success('人脸跟踪已停止')
          
          // 停止状态监控
          this.stopTrackingStatusMonitor()
        } else {
          throw new Error(result.message || '停止人脸跟踪失败')
        }
      } catch (error) {
        console.error('停止人脸跟踪失败:', error)
        // this.$toast.error(`停止失败: ${error.message}`)
      } finally {
        this.servoLoading = false
      }
    },
    
    // 状态监控
    startTrackingStatusMonitor() {
      this.trackingStatusInterval = setInterval(async () => {
        if (!this.faceTrackingActive) return
        
        try {
          await this.getServoStatus()
          
          // 根据状态更新显示文本
          if (this.servoStatus.face_detected_during_scan) {
            this.faceTrackingStatus = '人脸跟踪中...'
          } else if (this.servoStatus.auto_face_tracking) {
            this.faceTrackingStatus = '环境扫描中...'
          } else {
            this.faceTrackingStatus = '跟踪完成'
            this.faceTrackingActive = false
            this.stopTrackingStatusMonitor()
          }
        } catch (error) {
          console.error('状态监控错误:', error)
        }
      }, 1000)
    },
    
    stopTrackingStatusMonitor() {
      if (this.trackingStatusInterval) {
        clearInterval(this.trackingStatusInterval)
        this.trackingStatusInterval = null
      }
    },
    
    async getServoStatus() {
      try {
        const response = await fetch('/api/servo/status')
        const result = await response.json()
        this.servoStatus = result
        
        // 同步状态
        if (result.current_angle_hori !== undefined) {
          this.currentAngleHori = result.current_angle_hori
        }
        if (result.current_angle_vert !== undefined) {
          this.currentAngleVert = result.current_angle_vert
        }
        this.autoLoopActive = result.is_looping || false
        this.faceTrackingActive = result.auto_face_tracking || false
        
      } catch (error) {
        console.error('获取舵机状态失败:', error)
      }
    },
    
    // 辅助方法
    getModeStatusClass() {
      switch (this.servoMode) {
        case 'manual': return 'status-manual'
        case 'auto': return this.autoLoopActive ? 'status-active' : 'status-inactive'
        case 'face-track': return this.faceTrackingActive ? 'status-active' : 'status-inactive'
        default: return 'status-inactive'
      }
    },
    
    getModeStatusText() {
      switch (this.servoMode) {
        case 'manual': return '手动'
        case 'auto': return this.autoLoopActive ? '运行中' : '就绪'
        case 'face-track': return this.faceTrackingActive ? '跟踪中' : '就绪'
        default: return '就绪'
      }
    }
  },
  beforeRouteLeave(to, from, next) {
    // 路由离开前停止所有舵机活动
    this.stopAllServoActivity().finally(() => {
      next()
    })
  },
  mounted() {
    this.getServoStatus()
    // 页面加载时确保停止所有舵机活动
    this.stopAllServoActivity()
  },
  
  beforeUnmount() {
    // 组件销毁前停止所有舵机活动
    this.stopAllServoActivity()
  },
  unmounted() {
    this.stopRecognitionCheck()
  }
}
</script>


<style scoped>
.face-recognition-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

/* 舵机控制面板样式 */
.servo-control-panel {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 15px;
  padding: 25px;
  color: white;
  box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}

.servo-control-panel h3 {
  margin: 0 0 20px 0;
  font-size: 1.5em;
  text-align: center;
}

/* 模式选择器 */
.mode-selector {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  padding: 15px;
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  backdrop-filter: blur(10px);
}

.mode-dropdown {
  padding: 8px 15px;
  border: none;
  border-radius: 8px;
  background: white;
  color: #333;
  font-size: 16px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.mode-dropdown:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(255,255,255,0.3);
}

.mode-status {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.status-manual { background: #4CAF50; }
.status-active { background: #FF9800; animation: pulse 2s infinite; }
.status-inactive { background: #757575; }

/* 手动控制样式 */
.manual-control {
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 20px;
}

.angle-control {
  margin-bottom: 25px;
  padding: 15px;
  background: rgba(255,255,255,0.05);
  border-radius: 8px;
  border-left: 4px solid #4CAF50;
}

.angle-control:last-child {
  border-left-color: #FF9800; /* 垂直舵机用橙色边框 */
}

.angle-control label {
  display: block;
  margin-bottom: 15px;
  font-weight: bold;
}

.slider-container {
  margin-bottom: 20px;
}

.angle-slider {
  width: 100%;
  height: 8px;
  border-radius: 5px;
  background: rgba(255,255,255,0.3);
  outline: none;
  -webkit-appearance: none;
  appearance: none;
}

.angle-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 25px;
  height: 25px;
  border-radius: 50%;
  background: #4CAF50;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0,0,0,0.3);
}

.angle-slider::-moz-range-thumb {
  width: 25px;
  height: 25px;
  border-radius: 50%;
  background: #4CAF50;
  cursor: pointer;
  border: none;
}

/* 垂直舵机滑块样式 */
.vertical-slider {
  background: rgba(255,165,0,0.3); /* 橙色背景区分垂直舵机 */
}

.vertical-slider::-webkit-slider-thumb {
  background: #FF9800; /* 橙色滑块 */
}

.vertical-slider::-moz-range-thumb {
  background: #FF9800;
}

.angle-display {
  text-align: center;
  margin-top: 10px;
}

.angle-value {
  font-size: 24px;
  font-weight: bold;
  display: block;
  margin-bottom: 10px;
}

.angle-indicators {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  opacity: 0.7;
}

.quick-angles {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

.quick-btn {
  padding: 8px 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  background: transparent;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  font-weight: bold;
}

.quick-btn:hover {
  background: rgba(255,255,255,0.2);
  transform: translateY(-2px);
}

.quick-btn.active {
  background: #4CAF50;
  border-color: #4CAF50;
}

/* 自动控制样式 */
.auto-control {
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 20px;
}

.loop-settings {
  margin-bottom: 20px;
}

.loop-settings label {
  display: block;
  margin-bottom: 10px;
  font-weight: bold;
}

.duration-input {
  padding: 8px 12px;
  border: none;
  border-radius: 6px;
  background: white;
  color: #333;
  font-size: 16px;
  width: 100px;
}

.loop-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.loop-btn, .track-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  border: none;
  border-radius: 25px;
  background: #4CAF50;
  color: white;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 160px;
  justify-content: center;
}

.loop-btn:hover, .track-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
}

.loop-btn.stop, .track-btn.stop {
  background: #f44336;
}

.loop-btn:disabled, .track-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.loop-status, .tracking-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #4CAF50;
  animation: pulse 2s infinite;
}

.status-indicator.scanning {
  background: #FF9800;
  animation: scanning 1.5s infinite;
}

/* 人脸跟踪控制样式 */
.face-track-control {
  background: rgba(255,255,255,0.1);
  border-radius: 10px;
  padding: 20px;
}

.track-info {
  margin-bottom: 20px;
  font-size: 14px;
}

.track-info ul {
  margin: 10px 0;
  padding-left: 20px;
}

.track-info li {
  margin: 5px 0;
}

/* 舵机状态显示 */
.servo-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 20px;
  padding: 15px;
  background: rgba(0,0,0,0.2);
  border-radius: 8px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-item .label {
  opacity: 0.8;
}

.status-item .value {
  font-weight: bold;
  font-size: 18px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* 动画 */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes scanning {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.2); opacity: 0.7; }
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .mode-selector {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  
  .quick-angles {
    justify-content: space-around;
  }
  
  .quick-btn {
    flex: 1;
    min-width: 60px;
  }
  
  .servo-status {
    flex-direction: column;
    gap: 10px;
  }
}
</style>