<script setup>
import {
  UserIcon,
 } from "@heroicons/vue/24/outline"
 import { marked } from "marked";

import ProgressSpinner from 'primevue/progressspinner';
import OverlayPanel from "primevue/overlaypanel";

import CollectionTableCell from "../CollectionTableCell.vue";

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../../api/httpClient"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../../stores/app_state_store"
import { useMapStateStore } from "../../../stores/map_state_store"
import { useCollectionStore } from "../../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["item", "column", "columns_with_running_processes", "item_size_mode", "hide_execute_button"],
  emits: [],
  data() {
    return {
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
    is_empty() {
      return !this.item.column_data[this.column.identifier]?.value
    },
    is_processing() {
      return this.is_empty && this.columns_with_running_processes.includes(this.column.identifier)
    }
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <button class="w-full h-full text-left px-2 relative max-w-[420px] flex flex-row justify-start items-center" id="cell"
    @click="event => {$refs.cell_detail_overlay.toggle(event)}"
    :class="{'min-w-[120px]': !item.column_data[column.identifier] || value_as_html.length <= 10,
             'min-w-[270px]': value_as_html.length > 10 && value_as_html.length <= 100,
             'min-w-[350px]': value_as_html.length > 100}">

    <div v-html="value_as_html" v-if="!is_empty"
      class="flex-1 text-xs line-clamp-1 use-default-html-styles text-gray-700">
    </div>

    <div v-if="is_processing"
      class="flex-1 flex flex-row items-center justify-center">
      <ProgressSpinner class="w-6 h-6"></ProgressSpinner>
    </div>

    <div v-if="item.column_data[column.identifier]?.is_ai_generated"
      v-tooltip.bottom="{'value': 'AI generated'}"
      class="h-4 w-4 rounded bg-gray-100/50 text-gray-300 text-xs flex flex-row items-center justify-center">
      ✨
    </div>

    <div v-if="item.column_data[column.identifier]?.is_manually_edited"
      v-tooltip.bottom="{'value': 'manually edited'}"
      class="h-4 w-4 p-[1px] rounded bg-gray-100/50 text-gray-300 text-xs flex flex-row items-center justify-center">
      <UserIcon></UserIcon>
    </div>

    <OverlayPanel ref="cell_detail_overlay">
      <CollectionTableCell
          :item="item" :column="column"
          :columns_with_running_processes="columns_with_running_processes"
          :item_size_mode="item_size_mode">
      </CollectionTableCell>
    </OverlayPanel>

  </button>
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
</style>
