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
        right: mapState.mapRightFromRelative(mapState.per_point.x[mapState.hovered_point_idx]) + 'px',  // assuming map ends at right screen edge for now
        top: mapState.mapTopFromRelative(mapState.per_point.y[mapState.hovered_point_idx]) + mapState.map_client_y + 'px',
        'max-width': '200px',
      }">
      <div
        v-if="appState.get_hover_rendering_by_index(mapState.hovered_point_idx)"
        class="flex flex-col rounded bg-white px-2 py-1 text-xs text-gray-500 shadow-xl">
        <div
          class="text-xs font-semibold"
          v-html="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).title(mapState.get_item_by_index(mapState.hovered_point_idx))">
        </div>
        <div
          class="mt-1 text-xs font-normal"
          v-show="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).subtitle(mapState.get_item_by_index(mapState.hovered_point_idx))"
          v-html="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).subtitle(mapState.get_item_by_index(mapState.hovered_point_idx))">
        </div>
        <div class="flex flex-row justify-center">
          <img
            v-if="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).image(mapState.get_item_by_index(mapState.hovered_point_idx))"
            :src="appState.get_hover_rendering_by_index(mapState.hovered_point_idx).image(mapState.get_item_by_index(mapState.hovered_point_idx))"
            class="h-24 w-auto" />
        </div>
      </div>
      <div
        v-if="!appState.get_hover_rendering_by_index(mapState.hovered_point_idx)"
        class="rounded bg-white px-1 text-xs text-gray-500">
        loading...
      </div>
    </div>
</template>

<style scoped></style>
