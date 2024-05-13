<script setup>
import { ArrowDownCircleIcon } from "@heroicons/vue/24/outline"

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
  },
}
</script>

<template>
  <div class="relative"
    :class="{'min-w-[120px]': item.column_data[column.identifier]?.value.length > 5 && item.column_data[column.identifier]?.value.length <= 100,
                'min-w-[250px]': item.column_data[column.identifier]?.value.length > 100}">
    <div ref="scroll_area" class="max-h-[210px] overflow-y-scroll">
      <ProgressSpinner v-if="!item.column_data[column.identifier]?.value && current_extraction_processes.includes(column.identifier)"
        class="w-6 h-6"></ProgressSpinner>
      <div v-else v-html="value_as_html"></div>
    </div>
    <div v-if="show_more_indicator" class="absolute bottom-0 right-0 h-6 w-6 rounded-full bg-white text-gray-400"
      v-tooltip="{'value': 'Scroll down for more'}">
      <ArrowDownCircleIcon></ArrowDownCircleIcon>
    </div>
  </div>
</template>

<style scoped>
</style>
