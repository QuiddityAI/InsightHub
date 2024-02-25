<script setup>
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
  <div>
    <div v-for="filter, index in mapState.visibility_filters">
      <span>{{ filter.display_name }}</span>
      <button @click="remove_filter(index)">X</button>
    </div>
  </div>

</template>

<style scoped>
</style>
