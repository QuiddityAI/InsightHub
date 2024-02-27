<script setup>
import Chip from 'primevue/chip';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
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
  },
  mounted() {
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
  <div v-if="mapState.visibility_filters.length" class="mt-3 flex flex-row flex-wrap gap-2">
    <Chip v-for="filter, index in mapState.visibility_filters"
      :label="filter.display_name"
      removable @remove="remove_filter(index)">
    </Chip>
  </div>

</template>

<style scoped>
</style>
