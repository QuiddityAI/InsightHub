<script setup>
import Chip from 'primevue/chip';

import VueWordCloud from 'vuewordcloud';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { httpClient } from "../../api/httpClient"

const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      selection_statistics: {},
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on("visible_result_ids_updated", () => {
      const that = this
      this.selection_statistics = {}
      if (!this.appStateStore.map_id) {
        return
      }
      if (!this.appStateStore.visible_result_ids.length || this.appStateStore.visible_result_ids.length == this.appStateStore.search_result_ids.length) {
        return
      }
      const body = {
        map_id: this.appStateStore.map_id,
        selected_ids: this.appStateStore.visible_result_ids,
      }
      httpClient
        .post(`/data_backend/map/selection_statistics`, body)
        .then(function (response) {
          that.selection_statistics = response.data
        })
    })
  },
  watch: {
  },
  methods: {
    remove_filter(index) {
      this.mapStateStore.visibility_filters.splice(index, 1)
      this.eventBus.emit("visibility_filters_changed")
    },
    add_word_filter(word) {
      this.mapStateStore.visibility_filters.push({
        display_name: `Contains: ${word}`,
        filter_fn: (item) => {
          const dataset = this.appStateStore.datasets[item._dataset_id]
          for (const field of dataset.default_search_fields) {
            const value = item[field]
            const is_string = typeof value === "string" || value instanceof String
            if (value && is_string && value.toLowerCase().includes(word.toLowerCase())) {
              return true
            }
          }
          return false
        }
      })
      this.eventBus.emit("visibility_filters_changed")
    },
  },
}
</script>

<template>
  <div v-if="mapState.visibility_filters.length" class="mt-3 mb-1">
    <div class="flex flex-row flex-wrap gap-2">
      <Chip v-for="filter, index in mapState.visibility_filters"
        class="text-sm">
        {{ filter.display_name }}
        <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for future filter list -->
        <button v-if="!filter.is_text_filter" @click="remove_filter(index)" v-tooltip="{value: 'Remove Filter', showDelay: 400}"
            class="ml-2 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
      </Chip>
    </div>
    <div v-if="selection_statistics.important_words"
      class="ml-1 mt-2 text-sm text-gray-500">
      <b>Important keywords in selected items:</b><br>
      <VueWordCloud :words="selection_statistics.important_words"
        font-family="Lexend"
        color="Gray"
        :spacing="0.7"
        style="width: 100%; height: 150px;">
        <template v-slot="props">
          <button
            class="px-1 text-gray-500 rounded-md hover:bg-gray-100"
            @click="add_word_filter(props.text)">
            {{ props.text }}
          </button>
        </template>
      </VueWordCloud>
    </div>
  </div>

</template>

<style scoped>
</style>
