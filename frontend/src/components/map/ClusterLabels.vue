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
  <div class="pointer-events-none">
    <div
      v-for="cluster_label in mapState.clusterData"
      class="pointer-events-auto fixed"
      :style="{
        left: mapState.screenLeftFromRelative(cluster_label.center[0]) + 'px',
        bottom: mapState.screenBottomFromRelative(cluster_label.center[1]) + 'px',
      }">
      <button
        v-if="
          appState.selected_cluster_id === null ||
          cluster_label.id === appState.selected_cluster_id
        "
        @click="appState.cluster_selected(cluster_label)"
        @mouseenter="appState.cluster_hovered(cluster_label.id)"
        @mouseleave="appState.cluster_hover_end()"
        class="rounded bg-white px-1 text-xs text-gray-500 hover:bg-gray-100"
        v-html="cluster_label.title_html"></button>
    </div>
  </div>
</template>

<style scoped></style>
