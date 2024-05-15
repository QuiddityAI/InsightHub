<script setup>
import {
  ArrowDownCircleIcon,
  PencilIcon,
  CheckIcon,
  UserIcon,
 } from "@heroicons/vue/24/outline"

import ProgressSpinner from 'primevue/progressspinner';
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
  props: ["item", "column", "current_extraction_processes"],
  emits: [],
  data() {
    return {
      show_more_indicator: false,
      edit_mode: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    value_as_html() {
      const value = this.item.column_data[this.column.identifier]?.value || ""
      return value.replace(/(?:\r\n|\r|\n)/g, '<br>')
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
  },
}
</script>

<template>
  <div class="relative" id="cell"
    :class="{'min-w-[120px]': item.column_data[column.identifier]?.value.length > 5 && item.column_data[column.identifier]?.value.length <= 100,
                'min-w-[250px]': item.column_data[column.identifier]?.value.length > 100}">
    <div ref="scroll_area" class="min-h-[70px] max-h-[210px] overflow-y-scroll">
      <ProgressSpinner v-if="!item.column_data[column.identifier]?.value && current_extraction_processes.includes(column.identifier)"
        class="w-6 h-6"></ProgressSpinner>
      <div v-else>
        <div v-if="!edit_mode" v-html="value_as_html"></div>
        <textarea v-if="edit_mode" :value="item.column_data[column.identifier]?.value" ref="edit_text_area"></textarea>
      </div>
    </div>
    <div v-if="show_more_indicator" class="absolute bottom-6 right-0 h-6 w-6 rounded-full bg-white text-gray-400"
      v-tooltip="{'value': 'Scroll down for more'}">
      <ArrowDownCircleIcon></ArrowDownCircleIcon>
    </div>
    <button v-if="!edit_mode" @click="edit_mode = true" id="editicon"
      v-tooltip.right="{'value': 'Edit', showDelay: 500}"
      class="absolute top-0 right-0 h-6 w-6 rounded bg-gray-100 text-gray-500 hover:text-blue-500">
      <PencilIcon class="m-1"></PencilIcon>
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

<style scoped>
#editicon {
  display: none;
}

#cell:hover > #editicon {
  display: block;
}
</style>
