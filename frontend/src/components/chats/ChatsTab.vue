<script setup>

import Message from 'primevue/message';

import Chat from "./Chat.vue"

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
  props: ["collection_id", "class_name"],
  emits: [],
  data() {
    return {
      collection_chats: [],
      selected_chat_id: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    chat_list() {
      return this.collection_id ? this.collection_chats : this.appStateStore.chats
    },
  },
  mounted() {
    // this could be the global chat list or one for a collection
    if (this.collection_id && this.class_name) {
      this.get_collection_chats()
    } else {
      // this is only relevant for the global chat list:
      this.eventBus.on("show_chat", ({chat_id}) => {
        this.selected_chat_id = null  // close any open chat
        setTimeout(() => this.selected_chat_id = chat_id, 100)  // open the new chat
      })
    }
  },
  watch: {
  },
  methods: {
    get_collection_chats() {
      const that = this
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
      }
      httpClient.post(`/org/data_map/get_collection_class_chats`, body)
      .then(function (response) {
        that.collection_chats = response.data
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
        that.collection_chats.unshift(response.data)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <div class="mt-3 mb-3 pt-4 pb-3 pl-5 pr-7 shadow-sm rounded-md bg-white overflow-hidden">

    <div v-if="!appState.logged_in" class="h-full flex flex-row gap-5 items-center justify-center">
      <Message :closable="false">
        Log in to use chats
      </Message>
    </div>

    <div v-if="appState.logged_in" class="h-full flex flex-row gap-7 items-center justify-center">

      <div class="h-full flex flex-col overflow-y-auto w-[400px]">

        <div v-if="!selected_chat_id && collection_id" class="my-2 flex items-stretch">
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

        <button @click=""
          class="mt-2 bg-gray-100 font-semibold hover:bg-blue-100/50 rounded-md w-full py-1 text-left pl-2 text-gray-600 mb-2">
          New Chat +
        </button>

        <button v-for="chat in chat_list" :key="chat.id" @click="selected_chat_id = chat.id"
          class="mt-2 bg-gray-100 hover:bg-blue-100/50 rounded-md w-full py-2 text-left pl-2 pr-2 text-gray-600 mb-2">
          {{ chat.name || 'Chat ' + chat.id }}
        </button>

      </div>

      <div class="h-full flex-1 flex flex-col">
        <div
          v-if="!selected_chat_id"
          class="flex-1 flex flex-col place-content-center text-center">
          <p class="flex-none text-gray-400">Select a chat on the left</p>
        </div>

        <Chat v-if="selected_chat_id"
          class="flex-1"
          @close="selected_chat_id = null"
          :chat_id="selected_chat_id">
        </Chat>
      </div>


    </div>

  </div>

</template>

<style scoped>
</style>
