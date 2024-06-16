<script setup>
import {
  ChevronDownIcon,
} from "@heroicons/vue/24/outline"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import Statistic from "./Statistic.vue";
const appState = useAppStateStore()
const mapState = useMapStateStore()
</script>

<script>


export default {
  inject: ["eventBus"],
  emits: [],
  data() {
    return {
      statistic_idx_per_dataset: {},
      hide_per_dataset: {},
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
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
  <div v-if="appState.search_result_ids.length" v-for="dataset_id in mapState.map_parameters?.search.dataset_ids || []">
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
        <!-- <button @click="statistic_idx_per_dataset[dataset_id] = undefined"
          class="rounded px-2 py-[2px] text-sm text-gray-500 hover:bg-blue-100/50">
            <ChevronDownIcon class="w-5 h-5" />
          </button> -->
      </div>
      <Statistic
        v-if="appState.datasets[dataset_id]?.schema.statistics?.groups[statistic_idx_per_dataset[dataset_id]]"
        v-for="statistic in appState.datasets[dataset_id]?.schema.statistics?.groups[statistic_idx_per_dataset[dataset_id] || 0].plots"
        :key="statistic"
        :statistic="statistic" />
    </div>
  </div>
</template>

<style scoped></style>
