<script setup>
import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import OverlayPanel from 'primevue/overlaypanel';

import CollectionItem from '../collections/CollectionItem.vue';
import ChatContextCard from './ChatContextCard.vue';

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
  emits: ["close"],
  data() {
    return {
      chat_data: null,
      selected_citation: null,
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
    chat_id: function (newValue, oldValue) {
      this.chat_data = null
      this.selected_citation = null
      this.get_chat()
    },
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
    list_of_text_and_citation_parts(text) {
      text.replace(/(?:\r\n|\r|\n)/g, '<br>')
      const regex = /\[([0-9]+), "?([0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12})"?\]/ig;

      let i = 1
      const citations = []
      for (const matches of text.matchAll(regex)) {
        const whole_match = matches[0]
        const dataset_id = parseInt(matches[1])
        const item_id = matches[2]
        const replacement = " <split> "
        text = text.replace(whole_match, replacement)
        citations.push({
          is_citation: true,
          citation_index: i,
          dataset_id: dataset_id,
          item_id: item_id,
        })
        i++
      }
      const text_array = text.split(" <split> ")
      const interleaved_array = []
      for (const [index, item] of text_array.entries()) {
        interleaved_array.push({
          is_citation: false,
          content: item,
        })
        if (citations[index]) {
          interleaved_array.push(citations[index])
        }
      }
      return interleaved_array
    },
  },
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <div v-if="chat_data" class="flex flex-col gap-4 ">

      <div class="ml-1 mt-3 flex flex-row items-center gap-3">
        <button
          @click="$emit('close')"
          class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
          <ChevronLeftIcon></ChevronLeftIcon>
        </button>
        <h2 class="font-bold text-gray-600">{{ chat_data.name }}</h2>
        <div class="flex-1"></div>
        <button
          @click.stop="$emit('remove')"
          v-tooltip.right="{ value: 'Delete this chat', showDelay: 400 }"
          class="text-sm text-gray-400 hover:text-red-600">
          <TrashIcon class="h-4 w-4"></TrashIcon>
        </button>
      </div>

      <ChatContextCard
        :chat_data="chat_data"
        >
      </ChatContextCard>

      <div class="flex flex-col gap-4">
        <div v-for="message in chat_data.is_processing ? [...chat_data.chat_history, {content: 'Processing...', role: 'system'}] : chat_data.chat_history"
          class="flex"
          :class="{
            'flex-row-reverse': message.role == 'user',
            'flex-row': message.role == 'system',
            'ml-[25%]': message.role == 'user',
            'mr-[25%]': message.role == 'system',
            }"
          >
          <div
            class="px-3 py-3 rounded-md text-sm text-gray-700"
            :class="{'text-right': message.role == 'user', 'bg-blue-100/50': message.role == 'user', 'bg-gray-100': message.role == 'system'}">
            <span v-for="part in list_of_text_and_citation_parts(message.content)">
              <span v-if="part.is_citation">
                <button
                  @click="(event) => { selected_citation = part; $refs.citation_tooltip.toggle(event) }"
                  title="Click to show reference"
                  class="text-blue-500 cursor-pointer"
                  type="button">
                  [{{ part.citation_index }}]
                </button>
              </span>
              <span v-else v-html="part.content">
              </span>
            </span>
          </div>
        </div>
      </div>

      <OverlayPanel ref="citation_tooltip">
        <CollectionItem
          class="w-[500px]"
          :dataset_id="selected_citation.dataset_id"
          :item_id="selected_citation.item_id">
        </CollectionItem>
      </OverlayPanel>

    </div>

    <div class="flex-1"></div>

    <div v-if="chat_data?.chat_history?.length == 0 || appState.user.is_staff" class="my-2 flex items-stretch">
      <input
        ref="new_question_name"
        type="text"
        class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Ask a question"
        @keyup.enter="add_question($refs.new_question_name.value); $refs.new_question_name.value = ''"/>
      <button
        class="rounded-r-md border-0 px-4 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="add_question($refs.new_question_name.value); $refs.new_question_name.value = ''">
        Ask
      </button>
    </div>
  </div>

</template>

<style scoped>
</style>
