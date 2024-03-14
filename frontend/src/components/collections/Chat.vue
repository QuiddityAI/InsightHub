<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["chat_id"],
  emits: [],
  data() {
    return {
      chat_data: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.get_chat()
  },
  watch: {
  },
  methods: {
    get_chat() {
      const that = this
      const body = {
        chat_id: this.chat_id,
      }
      httpClient.post(`/org/data_map/get_chat_by_id`, body)
      .then(function (response) {
        that.chat_data = response.data
        if (that.chat_data.is_processing) {
          setTimeout(() => {
            that.get_chat()
          }, 1000)
        }
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    add_question(question) {
      const that = this
      const body = {
        chat_id: this.chat_id,
        question: question,
      }
      httpClient.post(`/org/data_map/add_chat_question`, body)
      .then(function (response) {
        that.chat_data = response.data
        if (that.chat_data.is_processing) {
          setTimeout(() => {
            that.get_chat()
          }, 1000)
        }
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <div>
    <div v-if="chat_data">
      <h2 class="mb-2">Chat: {{ chat_data.name }}</h2>

      <div v-for="message in chat_data.chat_history"
      class="p-1 rounded-md bg-gray-100 mb-1 text-sm text-gray-700" :class="{'text-right': message.role == 'user', 'bg-blue-100/50': message.role == 'user'}">
        <span>{{ message.content }}</span>
      </div>

      <div v-if="chat_data.is_processing"
      class="p-1 rounded-md bg-gray-100 mb-1 text-sm text-gray-700">
        <span>Processing...</span>
      </div>

    </div>

    <div class="my-2 flex items-stretch">
      <input
        ref="new_question_name"
        type="text"
        class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Ask a question"
        @keyup.enter="add_question($refs.new_question_name.value); $refs.new_question_name.value = ''"/>
      <button
        class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="add_question($refs.new_question_name.value); $refs.new_question_name.value = ''">
        Ask
      </button>
    </div>
  </div>

</template>

<style scoped>
</style>
