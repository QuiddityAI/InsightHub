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
  <div
      v-if="mapState.hovered_point_idx !== -1"
      class="pointer-events-none fixed"
      :style="{
        right: mapState.screenRightFromRelative(mapState.per_point.x[mapState.hovered_point_idx]) + 'px',
        top: mapState.screenTopFromRelative(mapState.per_point.y[mapState.hovered_point_idx]) + 'px',
        'max-width': '200px',
      }">
      <div
        v-if="appState.get_hover_rendering_by_index(mapState.hovered_point_idx)"
        class="flex flex-col items-center rounded bg-white px-1 text-xs text-gray-500">
        <div
          v-html="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).title(mapState.get_item_by_index(mapState.hovered_point_idx))"></div>
        <img
          v-if="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).image(mapState.get_item_by_index(mapState.hovered_point_idx))"
          :src="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).image(mapState.get_item_by_index(mapState.hovered_point_idx))"
          class="h-24" />
      </div>
      <div
        v-if="!appState.get_hover_rendering_by_index(mapState.hovered_point_idx)"
        class="rounded bg-white px-1 text-xs text-gray-500">
        loading...
      </div>
    </div>
</template>

<style scoped></style>
