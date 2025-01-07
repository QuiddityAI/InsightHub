<script setup>
import {
  ArrowDownCircleIcon,
  PencilIcon,
  CheckIcon,
  UserIcon,
  DocumentDuplicateIcon,
 } from "@heroicons/vue/24/outline"
 import {Marked, marked} from "marked";
import markedKatex from "marked-katex-extension";

import ProgressSpinner from 'primevue/progressspinner';
import Dialog from "primevue/dialog";

import { CollectionItemSizeMode } from "../../utils/utils.js"

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"
import { FieldType } from "../../utils/utils";

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()

const _window = window
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["item", "column", "columns_with_running_processes", "item_size_mode", "hide_execute_button"],
  emits: [],
  data() {
    return {
      show_more_indicator: false,
      edit_mode: false,
      show_used_prompt: false,
      show_typing_animation: false,
      typing_animation_start: null,
      typed_characters: 0,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    value_as_html() {
      if (this.item.column_data[this.column.identifier]?.collapsed_label) {
        return this.item.column_data[this.column.identifier]?.collapsed_label
      }
      let value = this.item.column_data[this.column.identifier]?.value || ""
      if (this.column.module === 'relevance' && value && typeof value === "object") {
        return value.criteria_review.map(item => {
            const checkbox = item.fulfilled ? "☑ " : "☐ "
            const criteria = item.criteria ? marked.parse(checkbox + item.criteria) : ""
            const supporting_quote = item.supporting_quote || ""
            const reason = item.reason ? marked.parse(item.reason + (supporting_quote ? ' *[hover for quote]*': '')) : ""
            const fulfilledClass = item.fulfilled ? "text-green-700" : "text-red-700"

            return `<div class="${fulfilledClass} font-bold mt-1">${criteria}</div>` +
                    `<div class="text-gray-700" title="Quote: ${supporting_quote}">${reason}</div>`
                    //`<div class="text-gray-700">${supporting_quote}</div>`
          }).join('')
      } else if (typeof value === "string") {
        if (this.show_typing_animation) {
          value = value.slice(0, this.typed_characters)
        }
        return marked.parse(value)
      } else {
        return value
      }
    },
    value_as_plain_text() {
      const value = this.item.column_data[this.column.identifier]?.value || ""
      if (typeof value !== "string") {
        return value
      }
      const katex_options = {
        output: "html",  // otherwise MathML is included for accesibility, but messes with copyable text
      }
      const marked_custom = new Marked().use(markedKatex(katex_options))
      const html = marked_custom.parse(value)
      function extractContent(s) {
        // gets copyable plain text from html
        var span = document.createElement('span');
        span.innerHTML = s;
        return span.textContent || span.innerText;
      }
      return extractContent(html)
    },
    value_for_editing() {
      if (this.column.field_type === FieldType.ARBITRARY_OBJECT) {
        return JSON.stringify(this.item.column_data[this.column.identifier]?.value, null, 2)
      } else {
        return this.item.column_data[this.column.identifier]?.value || ""
      }
    },
    is_empty() {
      return !this.item.column_data[this.column.identifier]?.value
    },
    is_processing() {
      return this.is_empty && this.columns_with_running_processes.includes(this.column.identifier)
    }
  },
  mounted() {
    this.$nextTick(() => {
      this.update_show_more_indicator()
    })
    const resizeObserver = new ResizeObserver(() => {
      this.update_show_more_indicator()
    })
    resizeObserver.observe(this.$refs.scroll_area)
  },
  watch: {
    value_as_html() {
      this.$nextTick(() => {
        this.update_show_more_indicator()
      })
    },
    value_as_plain_text() {
      const column_data = this.item.column_data[this.column.identifier]
      if (column_data && column_data.is_ai_generated
        && !column_data.is_manually_edited) {
        const seconds_since_changed = (new Date() - new Date(column_data.changed_at )) / 1000
        if (seconds_since_changed < 5) {
          this.show_typing_animation = true
          this.typing_animation_start = new Date()
          this.typed_characters = 0
          const value = column_data.value || ""
          const interval = setInterval(() => {
            const seconds_since_start = (new Date() - this.typing_animation_start) / 1000
            this.typed_characters = Math.floor(seconds_since_start * 120)
            if (this.typed_characters >= value.length) {
              clearInterval(interval)
            }
          }, 100)
        }
      } else {
        this.show_typing_animation = false
      }
    },
  },
  methods: {
    update_show_more_indicator() {
      const scroll_area = this.$refs.scroll_area
      if (!scroll_area) return false
      this.show_more_indicator = scroll_area.scrollHeight > scroll_area.clientHeight
    },
    submit_changes() {
      const that = this
      let value = this.$refs.edit_text_area.value
      if (this.column.field_type === FieldType.ARBITRARY_OBJECT) {
        value = JSON.parse(value || "{}")
      }
      if (!this.item.column_data) {
        this.item.column_data = {}
      }
      if (!this.item.column_data[this.column.identifier]) {
        this.item.column_data[this.column.identifier] = {
          is_ai_generated: false,
        }
      }
      this.item.column_data[this.column.identifier].value = value
      this.item.column_data[this.column.identifier].is_manually_edited = true
      if (!value) {
        this.item.column_data[this.column.identifier].is_ai_generated = false
        this.item.column_data[this.column.identifier].is_manually_edited = false
        this.item.column_data[this.column.identifier].collapsed_label = ""
      }
      const body = {
        collection_item_id: this.item.id,
        column_identifier: this.column.identifier,
        cell_data: this.item.column_data[this.column.identifier],
      }
      httpClient.post(`/api/v1/columns/set_cell_data`, body)
      .then(function (response) {
        that.edit_mode = false
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    convert_to_html(text) {
      // escape html
      text = text.replace(/&/g, "&amp;")
      text = text.replace(/</g, "&lt;")
      text = text.replace(/>/g, "&gt;")
      // convert newlines to <br>
      return text.replace(/(?:\r\n|\r|\n)/g, '<br>')
    },
  },
}
</script>

<template>
  <div class="relative max-w-[420px]" id="cell"
    :class="{'min-w-[120px]': !item.column_data[column.identifier] || value_as_html.length <= 10,
             'min-w-[270px]': value_as_html.length > 10 && value_as_html.length <= 100,
             'min-w-[350px]': value_as_html.length > 100}">

    <div v-if="!edit_mode"
      ref="scroll_area" class="relative min-h-[70px] overflow-y-auto"
      :class="{
        'max-h-[70px]': item_size_mode <= CollectionItemSizeMode.SMALL,
        'max-h-[150px]': item_size_mode === CollectionItemSizeMode.MEDIUM,
        'max-h-[300px]': item_size_mode >= CollectionItemSizeMode.FULL,
      }">
      <div v-if="!edit_mode" v-html="value_as_html"
        class="text-sm use-default-html-styles py-2 pl-1 text-gray-700 w-full"></div>
    </div>

    <div v-if="edit_mode"
      ref="scroll_area" class="relative min-h-[70px] overflow-y-scroll"
      :class="{
        'h-[70px]': item_size_mode <= CollectionItemSizeMode.SMALL,
        'h-[150px]': item_size_mode === CollectionItemSizeMode.MEDIUM,
        'h-[300px]': item_size_mode >= CollectionItemSizeMode.FULL,
      }">
      <textarea v-if="edit_mode"
        class="w-full h-full p-1 border border-gray-300 rounded text-sm py-2 pl-1"
        :value="value_for_editing"
        ref="edit_text_area">
      </textarea>
    </div>

    <div v-if="is_processing"
      class="absolute top-0 w-full h-full flex flex-col items-center justify-center">
      <ProgressSpinner class="w-6 h-6"></ProgressSpinner>
    </div>

    <div v-if="is_empty && !edit_mode && !is_processing"
      class="absolute top-0 w-full h-full flex flex-row gap-2 justify-center items-center text-gray-500 text-sm">
      <button
        @click="edit_mode = true" class="hover:text-sky-500">
        Edit
      </button>
      <span v-if="column.module !== 'notes' && !hide_execute_button"> | </span>
      <button v-if="column.module !== 'notes' && !hide_execute_button"
        @click="collectionStore.extract_question(column.id, true, item.id)" class="hover:text-sky-500">
        Execute
      </button>
    </div>

    <div v-if="show_more_indicator" class="absolute bottom-6 right-1 h-6 w-6 rounded-full bg-white text-gray-400"
      v-tooltip="{'value': 'Scroll down for more'}">
      <ArrowDownCircleIcon></ArrowDownCircleIcon>
    </div>
    <button v-if="!edit_mode" @click="edit_mode = true"
      v-tooltip.right="{'value': 'Edit', showDelay: 500}"
      class="absolute top-1 right-1 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
      <PencilIcon class="m-1"></PencilIcon>
    </button>
    <button v-if="appState.user.is_staff && !edit_mode && item.column_data[column.identifier]?.used_prompt" @click="show_used_prompt = true"
      v-tooltip.right="{'value': 'Show the used prompt', showDelay: 500}"
      class="absolute top-8 right-1 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
      P
    </button>
    <Dialog v-model:visible="show_used_prompt" modal header="Used Prompt">
      <div class="overflow-y-auto max-h-[400px]">
        <div>Used Model: {{ item.column_data[column.identifier]?.used_llm_model || 'unknown' }}</div>
        <div
          v-html="convert_to_html(item.column_data[column.identifier]?.used_prompt)">
        </div>
      </div>
    </Dialog>
    <button v-if="!edit_mode" @click="_window.isSecureContext ? _navigator.clipboard.writeText(value_as_plain_text) : _window.prompt('Copy to clipboard: Ctrl+C, Enter', value_as_plain_text)"
      v-tooltip.right="{'value': 'Copy plain text to clipboard', showDelay: 500}"
      class="absolute top-1 right-8 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
      <DocumentDuplicateIcon class="m-1"></DocumentDuplicateIcon>
    </button>

    <button v-if="edit_mode" @click="submit_changes()"
      v-tooltip.right="{'value': 'Save changes', showDelay: 500}"
      class="absolute top-1 right-1 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-green-500">
      <CheckIcon class="m-1"></CheckIcon>
    </button>
    <div v-if="!edit_mode && item.column_data[column.identifier]?.is_ai_generated"
      v-tooltip.bottom="{'value': 'AI generated'}"
      class="absolute bottom-1 right-1 h-4 w-4 rounded bg-gray-100/50 text-gray-300 text-xs flex flex-row items-center justify-center">
      ✨
    </div>
    <div v-if="!edit_mode && item.column_data[column.identifier]?.is_manually_edited"
      v-tooltip.bottom="{'value': 'manually edited'}"
      class="absolute bottom-1 right-6 h-4 w-4 p-[1px] rounded bg-gray-100/50 text-gray-300 text-xs flex flex-row items-center justify-center">
      <UserIcon></UserIcon>
    </div>
  </div>
</template>

<style>
.use-default-html-styles h1 {
  font-size: 1.2em;
  margin: 0.67em 0;
}

.use-default-html-styles h2 {
  font-size: 1.17em;
  margin: 0.83em 0;
}

.use-default-html-styles ul {
  list-style-type: disc;
  padding: 0 0 0 1.4em;
}

.use-default-html-styles ol {
  list-style-type: decimal;
  padding: 0 0 0 1.4em;
}

</style>

<style scoped>
.show-when-parent-is-hovered {
  display: none;
}

#cell:hover > .show-when-parent-is-hovered{
  display: block;
}
</style>
