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

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()

const _window = window
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["item", "column", "current_extraction_processes"],
  emits: [],
  data() {
    return {
      show_more_indicator: false,
      edit_mode: false,
      show_used_prompt: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    value_as_html() {
      if (this.item.column_data[this.column.identifier]?.collapsed_label) {
        return this.item.column_data[this.column.identifier]?.collapsed_label
      }
      const value = this.item.column_data[this.column.identifier]?.value || ""
      return marked.parse(value)
    },
    value_as_plain_text() {
      const value = this.item.column_data[this.column.identifier]?.value || ""
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
  },
  mounted() {
    this.$nextTick(() => {
      this.update_show_more_indicator()
    })
  },
  watch: {
    value_as_html() {
      this.$nextTick(() => {
        this.update_show_more_indicator()
      })
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
      const value = this.$refs.edit_text_area.value
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
        item_id: this.item.id,
        column_identifier: this.column.identifier,
        cell_data: this.item.column_data[this.column.identifier],
      }
      httpClient.post(`/org/data_map/set_collection_cell_data`, body)
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
  <div class="relative max-w-[400px]" id="cell"
    :class="{'min-w-[120px]': item.column_data[column.identifier]?.value.length > 5 && item.column_data[column.identifier]?.value.length <= 100,
                'min-w-[250px]': item.column_data[column.identifier]?.value.length > 100}">
    <div ref="scroll_area" class="min-h-[70px] max-h-[210px] overflow-y-scroll">
      <div v-if="!item.column_data[column.identifier]?.value && current_extraction_processes.includes(column.identifier)"
        class="flex flex-col items-center justify-center">
        <ProgressSpinner
        class="w-6 h-6"></ProgressSpinner>
      </div>
      <div v-else>
        <div v-if="!edit_mode" v-html="value_as_html" class="text-sm use-default-html-styles"></div>
        <textarea v-if="edit_mode"
          class="w-full h-[150px] p-1 border border-gray-300 rounded text-sm"
          :value="item.column_data[column.identifier]?.value"
          ref="edit_text_area">
        </textarea>
      </div>
    </div>

    <div v-if="show_more_indicator" class="absolute bottom-6 right-0 h-6 w-6 rounded-full bg-white text-gray-400"
      v-tooltip="{'value': 'Scroll down for more'}">
      <ArrowDownCircleIcon></ArrowDownCircleIcon>
    </div>
    <button v-if="!edit_mode" @click="edit_mode = true"
      v-tooltip.right="{'value': 'Edit', showDelay: 500}"
      class="absolute top-0 right-0 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
      <PencilIcon class="m-1"></PencilIcon>
    </button>
    <button v-if="appState.user.is_staff && !edit_mode && item.column_data[column.identifier]?.used_prompt" @click="show_used_prompt = true"
      v-tooltip.right="{'value': 'Show the used prompt', showDelay: 500}"
      class="absolute top-8 right-0 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
      P
    </button>
    <Dialog v-model:visible="show_used_prompt" modal header="Used Prompt">
      <div class="overflow-y-auto max-h-[400px]"
        v-html="convert_to_html(item.column_data[column.identifier]?.used_prompt)" />
    </Dialog>
    <button v-if="!edit_mode" @click="_window.isSecureContext ? _navigator.clipboard.writeText(value_as_plain_text) : _window.prompt('Copy to clipboard: Ctrl+C, Enter', value_as_plain_text)"
      v-tooltip.right="{'value': 'Copy plain text to clipboard', showDelay: 500}"
      class="absolute top-0 right-8 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500 show-when-parent-is-hovered">
      <DocumentDuplicateIcon class="m-1"></DocumentDuplicateIcon>
    </button>

    <button v-if="edit_mode" @click="submit_changes()"
      v-tooltip.right="{'value': 'Save changes', showDelay: 500}"
      class="absolute top-0 right-0 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-green-500">
      <CheckIcon class="m-1"></CheckIcon>
    </button>
    <div v-if="!edit_mode && item.column_data[column.identifier]?.is_ai_generated"
      v-tooltip.bottom="{'value': 'AI generated'}"
      class="absolute bottom-0 right-0 h-4 w-4 rounded bg-gray-100/50 text-gray-300 text-xs flex flex-row items-center justify-center">
      ✨
    </div>
    <div v-if="!edit_mode && item.column_data[column.identifier]?.is_manually_edited"
      v-tooltip.bottom="{'value': 'manually edited'}"
      class="absolute bottom-0 right-6 h-4 w-4 p-[1px] rounded bg-gray-100/50 text-gray-300 text-xs flex flex-row items-center justify-center">
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
