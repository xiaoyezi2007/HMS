import "vue-router";

declare module "vue-router" {
  interface RouteMeta {
    roles?: string[];
    public?: boolean;
    headOnly?: boolean;
  }
}
