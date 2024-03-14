<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

import Chat from "./Chat.vue"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["collection_id", "class_name"],
  emits: [],
  data() {
    return {
      chats: [],
      selected_chat_id: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.get_chat_ids()
  },
  watch: {
  },
  methods: {
    get_chat_ids() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient.post(`/org/data_map/get_collection_class_chats`, body)
      .then(function (response) {
        that.chats = response.data
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    create_chat(chat_name) {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        chat_name: chat_name,
      }
      httpClient.post(`/org/data_map/add_collection_class_chat`, body)
      .then(function (response) {
        that.chats.push(response.data)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <div class="mb-2">
    <div v-if="!selected_chat_id" class="my-2 flex items-stretch">
      <input
        ref="new_chat_name"
        type="text"
        class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Chat Name"
        @keyup.enter="create_chat($refs.new_chat_name.value); $refs.new_chat_name.value = ''"/>
      <button
        class="rounded-r-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="create_chat($refs.new_chat_name.value); $refs.new_chat_name.value = ''">
        Create Chat
      </button>
    </div>

    <button v-if="!selected_chat_id" v-for="chat in chats" :key="chat.id" @click="selected_chat_id = chat.id"
    class="bg-gray-100 hover:bg-blue-100/50 rounded-md w-full py-1 text-left pl-2 text-gray-600 mb-2">
      {{ chat.name || 'Chat ' + chat.id }}
    </button>

    <button v-if="selected_chat_id" @click="selected_chat_id = null"
    class="hover:bg-gray-100 rounded-md p-1">
      Back
    </button>

    <Chat v-if="selected_chat_id" :chat_id="selected_chat_id"></Chat>
  </div>

</template>

<style scoped>
</style>
