<script setup>
import {
  ChevronDownIcon,
} from "@heroicons/vue/24/outline"

import Statistic from "./Statistic.vue";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
</script>

<script>


export default {
  inject: ["eventBus"],
  emits: [],
  data() {
    return {
      dataset_ids: [],
      statistic_idx_per_dataset: {},
      hide_per_dataset: {},
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    const dataset_ids = new Set()
    const task = this.collectionStore.collection.most_recent_search_task
    if (task && task.dataset !== null) {
      if (this.appStateStore.datasets[task.dataset_id]?.schema.statistics?.groups?.length > 0) {
        dataset_ids.add(task.dataset)
      }
    }
    // only takes into account current page, but should be fine
    for (const item of this.collectionStore.collection_items) {
      if (this.appStateStore.datasets[item.dataset_id]?.schema.statistics?.groups?.length > 0) {
        dataset_ids.add(item.dataset_id)
      }
    }
    this.dataset_ids = Array.from(dataset_ids)
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div v-if="dataset_ids.length > 0" v-for="dataset_id in dataset_ids" :key="dataset_id">
    <div v-if="appState.datasets[dataset_id]?.schema.statistics?.groups?.length" class="mt-3 bg-gray-100/50 rounded-md">

      <div class="flex flex-row items-center gap-5 py-1">
        <span class="ml-3 text-sm text-gray-500">Statistics: </span>
        <button v-for="(group, index) in appState.datasets[dataset_id]?.schema.statistics?.groups"
          @click="statistic_idx_per_dataset[dataset_id] === index ? statistic_idx_per_dataset[dataset_id] = undefine : statistic_idx_per_dataset[dataset_id] = index"
          class="rounded px-2 py-[2px] text-sm text-gray-500 hover:text-blue-500"
          :class="{
            'bg-gray-200': !((statistic_idx_per_dataset[dataset_id]) === index),
            'bg-blue-100/50': (statistic_idx_per_dataset[dataset_id]) === index,
            }"
          >{{ group.title }}</button>
        <div class="flex-1"></div>
      </div>

      <Statistic
        v-if="appState.datasets[dataset_id]?.schema.statistics?.groups[statistic_idx_per_dataset[dataset_id]]"
        v-for="statistic in appState.datasets[dataset_id]?.schema.statistics?.groups[statistic_idx_per_dataset[dataset_id] || 0].plots"
        :dataset_id="dataset_id"
        :required_fields="appState.datasets[dataset_id]?.schema.statistics.required_fields"
        :key="statistic"
        :statistic="statistic" />
    </div>
  </div>
</template>

<style scoped></style>
