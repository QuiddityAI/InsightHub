<script setup>
import Chip from 'primevue/chip';

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
  },
}
</script>

<template>
  <div v-if="mapState.visibility_filters.length" class="mt-3 mb-1">
    <div class="flex flex-row flex-wrap gap-2">
      <Chip v-for="filter, index in mapState.visibility_filters"
        :label="filter.display_name"
        :removable="!filter.is_text_filter" @remove="remove_filter(index)">
      </Chip>
    </div>
    <div class="ml-1 mt-2 text-sm text-gray-500">
      <b>Important keywords in selected items:</b><br>
      {{ selection_statistics.title }}
    </div>
  </div>

</template>

<style scoped>
</style>
