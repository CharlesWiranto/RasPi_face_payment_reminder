import { createRouter, createWebHistory } from 'vue-router'
import FaceRecognition from '@/views/FaceRecognition.vue'
import UserRegistration from '@/views/UserRegistration.vue'
import PaymentsManagements from '@/views/PaymentsManagements.vue'

const routes = [
  {
    path: '/',
    name: 'FaceRecognition',
    component: FaceRecognition
  },
  {
    path: '/register',
    name: 'UserRegistration',
    component: UserRegistration
  },
  {
    path: '/payments',
    name: 'PaymentsManagements',
    component: PaymentsManagements
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router