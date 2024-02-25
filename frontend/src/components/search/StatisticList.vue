<script setup>
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
      selected_dataset_id: null,
      selected_statistics_group: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
    "appStateStore.settings.search.dataset_ids"(new_val, old_val) {
      this.selected_dataset_id = new_val[0]
      this.selected_statistics_group = this.appStateStore.datasets[this.selected_dataset_id]?.statistics?.groups[0]
    },
  },
  methods: {
  },
}
</script>

<template>
  <div>
    <span class="text-gray-600 text-sm">Statistics:</span>
    <select v-model="selected_dataset_id" class="border-transparent rounded text-gray-600 text-sm">
        <option v-for="dataset_id in appState.settings.search.dataset_ids" :value="dataset_id">{{ appState.datasets[dataset_id].name }}</option>
    </select>
    <select v-if="selected_dataset_id" v-model="selected_statistics_group" class="border-transparent rounded text-gray-600 text-sm">
      <option v-for="group in appState.datasets[selected_dataset_id]?.statistics?.groups" :value="group">{{ group.title }}</option>
    </select>
    <Statistic
      v-if="selected_statistics_group"
      v-for="statistic in selected_statistics_group.plots"
      :key="statistic"
      :statistic="statistic" />
  </div>
</template>

<style scoped></style>
