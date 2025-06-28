<template>
  <div class="min-h-screen bg-cover bg-center bg-gray-100 bg-opacity-90 bg-no-repeat p-4 md:p-8">
  <!-- <div class="min-h-screen bg-cover bg-center bg-no-repeat p-4 md:p-8" :style="{ backgroundImage: `url(${require('@/assets/PaymentsManagements_BG.png')})` }"></div> -->
    <div class="max-w-2xl mx-auto bg-white rounded-lg shadow-md p-6">
      <template v-if="paymentData">
        <h1 class="text-2xl font-bold text-center mb-6">Payment Details</h1>
        
        <div class="space-y-4 mb-6">
          <div class="flex justify-between border-b pb-2">
            <span class="font-medium">Recipient:</span>
            <span>{{ paymentData.user.name }}</span>
          </div>
          <div class="flex justify-between border-b pb-2">
            <span class="font-medium">Email:</span>
            <span>{{ paymentData.user.email }}</span>
          </div>
          <div class="flex justify-between border-b pb-2">
            <span class="font-medium">Amount:</span>
            <span>¥{{ paymentData.amount.toFixed(2) }}</span>
          </div>
          <div class="flex justify-between border-b pb-2">
            <span class="font-medium">Status:</span>
            <span :class="statusColor">{{ paymentData.status }}</span>
          </div>
          <div class="flex justify-between border-b pb-2">
            <span class="font-medium">Date:</span>
            <span>{{ formatDate(paymentData.created_at) }}</span>
          </div>
        </div>

        <div v-if="paymentData.status === 'pending'" class="text-center">
          <button 
            @click="initiatePayment"
            class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition-colors"
          >
            Pay Now
          </button>
          <p class="text-sm text-gray-500 mt-2">
            This payment is based on detected face in the system
          </p>
        </div>

        <div v-else-if="paymentData.status === 'completed'" class="text-center">
          <div class="bg-green-100 text-green-700 p-4 rounded-lg">
            <svg class="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
            </svg>
            <p class="font-medium">Payment Completed Successfully</p>
            <p class="text-sm mt-1">Payment ID: {{ this.paymentId }}</p>
          </div>
        </div>
      </template>

      <template v-else-if="loading">
        <div class="text-center py-8">
          <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
          <p class="mt-3">Loading payment details...</p>
        </div>
      </template>

      <template v-else>
        <div class="text-center py-8">
          <svg class="w-12 h-12 mx-auto text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
          </svg>
          <h2 class="text-xl font-medium mt-3">Payment Not Found</h2>
          <p class="text-gray-500 mt-1">The payment link is invalid or has expired</p>
          <router-link to="/" class="text-blue-600 hover:underline mt-4 inline-block">
            Return to Home
          </router-link>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import config from '@/config'

export default {
  name: 'PaymentsManagements',
  data() {
    return {
      paymentData: null,
      loading: true,
      error: null,
      paymentId: null
    }
  },
  computed: {
    statusColor() {
      if (!this.paymentData) return ''
      return {
        'pending': 'text-yellow-600',
        'completed': 'text-green-600',
        'failed': 'text-red-600'
      }[this.paymentData.status] || 'text-gray-600'
    }
  },
  methods: {
    formatDate(timestamp) {
      return new Date(timestamp).toLocaleString()
    },
    async fetchPaymentDetails(paymentId, token) {
      try {
        const response = await axios.get(`${config.RASP_URL}/api/payment/details`, {
          params: {
            payment_id: paymentId,
            token: token
          }
        })
        
        if (response.data.success) {
          this.paymentData = response.data.payment
        } else {
          this.error = response.data.error || 'Payment not found'
        }
      } catch (err) {
        console.error('Error fetching payment:', err)
        this.error = 'Failed to load payment details'
      } finally {
        this.loading = false
      }
    },
    async initiatePayment() {
      try {
        this.loading = true
        const response = await axios.post(`${config.RASP_URL}/api/payment/initiate`, {
          payment_id: this.paymentData.id,
          token: this.paymentData.token
        })
        
        if (response.data.success) {
          // Refresh the current page
          window.location.reload()
        } else {
          this.error = response.data.error || 'Failed to initiate payment'
        }
      } catch (err) {
        console.error('Payment initiation error:', err)
        this.error = 'Payment processing failed'
      } finally {
        this.loading = false
      }
    }
  },
  created() {
    // Extract payment ID and token from route query
    const paymentId = this.$route.query.payment_id
    const token = this.$route.query.token
    this.paymentId = paymentId
    if (paymentId && token) {
      this.fetchPaymentDetails(paymentId, token)
    } else {
      this.loading = false
      this.error = 'Invalid payment link'
    }
  }
}
</script>