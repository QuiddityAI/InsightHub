<script setup>
import RangeFilterItem from './RangeFilterItem.vue';

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
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    range_filters() {
      const filters = {}
      for (const dataset_id of this.mapStateStore.map_parameters?.search.dataset_ids || []) {
        for (const range_filter of this.appStateStore.datasets[dataset_id]?.merged_advanced_options?.range_filters || []) {
          filters[range_filter.field] = range_filter
        }
      }
      return Object.values(filters)
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
  <div v-if="appState.search_result_ids.length" class="mt-2 flex flex-col gap-2">
    <RangeFilterItem v-for="range_filter in range_filters"
      :range_filter="range_filter" />
  </div>

</template>

<style scoped>
</style>
