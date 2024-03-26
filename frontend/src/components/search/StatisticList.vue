<script setup>
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';

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
    <div v-if="appState.datasets[dataset_id]?.statistics?.groups?.length">
    <TabView class="mt-1">
      <TabPanel v-for="group in appState.datasets[dataset_id]?.statistics?.groups"
        :header="group.title">
        <Statistic
          v-if="group"
          v-for="statistic in group.plots"
          :key="statistic"
          :statistic="statistic" />
      </TabPanel>
    </TabView>
  </div>
  </div>
</template>

<style scoped></style>
